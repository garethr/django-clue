import logging
import time
from logging.handlers import BufferingHandler

from django.conf import settings
from django.core.signals import request_started
from django.shortcuts import render_to_response
from django.db import connection
from django.dispatch import dispatcher
from django.http import HttpResponseServerError
from django.test.signals import template_rendered
from django.utils.encoding import force_unicode
from django.db.backends.util import CursorDebugWrapper
import traceback    

# Monkey-patch the execute method to include a stack trace
def my_execute(self, sql, params=()):
    start = time.time()
    try:
        return self.cursor.execute(sql, params)
    finally:
        stop = time.time()
        executed_sql = self.db.ops.last_executed_query(
            self.cursor, sql, params
        )
        self.db.queries.append({
            'sql': executed_sql,
            'time': "%.3f" % (stop - start),
            'bad': (stop - start) > 0.01,
            'params': params,
            'sql_no_params': sql,
        })
CursorDebugWrapper.execute = my_execute

TEMPLATE = """
<pre>
Server-time taken: {{ server_time|floatformat:"5" }} seconds

{{ sql|length }} SQL queries executed in {{ sql_total }} seconds ({{ bad_sql_count }} queries took longer than 0.01):
{% if sql %}{% for query in sql %}
    {{ query.sql|linebreaksbr }} 
    took {% if query.bad %}{% endif %}{{ query.time|floatformat:"3" }} seconds{% if query.bad %} LONGQ{% endif %} 
{% endfor %}
{% if most_executed %}
{{ most_executed|length }} most frequently executed queries:
{% for pair in most_executed %} 
    {{ pair.0|linebreaksbr }}
    executed {{ pair.1|length }} times
{% endfor %}{% endif %}{% else %}
None{% endif %}
</pre>
"""

# Monkeypatch instrumented test renderer from django.test.utils - we could use
# django.test.utils.setup_test_environment for this but that would also set up
# e-mail interception, which we don't want
from django.test.utils import instrumented_test_render
from django.template import Template, Context
# MONSTER monkey-patch
old_template_init = Template.__init__
def new_template_init(self, template_string, origin=None, name='<Unknown Template>'):
    old_template_init(self, template_string, origin, name)
    self.origin = origin
Template.__init__ = new_template_init

class QueryMiddleware:
    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and request.REQUEST.has_key('query'):
            self.time_started = time.time()
            self.sql_offset_start = len(connection.queries)
        
            if not hasattr(self, 'loghandler'):
                self.loghandler = BufferingHandler(1000) # Create and a handler
                logging.getLogger('').addHandler(self.loghandler)
            else:
                self.loghandler.flush() # Empty it of all messages
            
    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and request.REQUEST.has_key('query'):
            sql_queries = connection.queries[self.sql_offset_start:]

            # Reformat sql queries a bit
            sql_total = 0.0
            for query in sql_queries:
                query['sql'] = reformat_sql(query['sql'])
                sql_total += float(query['time'])

            # Count the most-executed queries
            most_executed = {}
            for query in sql_queries:
                reformatted = reformat_sql(query['sql_no_params'])
                most_executed.setdefault(reformatted, []).append(query)
            most_executed = most_executed.items()
            most_executed.sort(key = lambda v: len(v[1]), reverse=True)
            most_executed = most_executed[:10]

            template_context = Context({
                'sql': sql_queries,
                'sql_total': sql_total,
                'bad_sql_count': len([s for s in sql_queries if s['bad']]),
                'most_executed': most_executed,
                'server_time': time.time() - self.time_started,
            })

            response.content = Template(TEMPLATE).render(template_context)            

        return response
    
def reformat_sql(sql):
    sql = sql.replace('`,`', '`, `')
    sql = sql.replace(' FROM ', ' \n    FROM ')
    sql = sql.replace(' WHERE ', ' \n    WHERE ')
    sql = sql.replace(' ORDER BY ', ' \n    ORDER BY ')
    sql = sql.replace(' ON ', ' \n    ON ')
    sql = sql.replace(' AND ', ' \n    AND ')
    sql = sql.replace(' LIMIT ', ' \n    LIMIT ')
    sql = sql.replace(' INNER JOIN ', ' \n    INNER JOIN ')
    sql = sql.replace(' LEFT OUTER JOIN ', ' \n    LEFT OUTER JOIN ')
    return sql
