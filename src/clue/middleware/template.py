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
<pre>Server-time taken: {{ server_time|floatformat:"5" }} seconds

Templates used:
{% if templates %}{% for template in templates %}
    * {{ template.0 }} loaded from {{ template.1 }}{% endfor %}{% else %}None{% endif %}

Template path:
{% if template_dirs %}{% for template in template_dirs %}
    * {{ template }}{% endfor %}{% else %}None{% endif %}
</pre>
"""

# Monkeypatch instrumented test renderer from django.test.utils - we could use
# django.test.utils.setup_test_environment for this but that would also set up
# e-mail interception, which we don't want
from django.test.utils import instrumented_test_render
from django.template import Template, Context
if Template.render != instrumented_test_render:
    Template.original_render = Template.render
    Template.render = instrumented_test_render
# MONSTER monkey-patch
old_template_init = Template.__init__
def new_template_init(self, template_string, origin=None, name='<Unknown Template>'):
    old_template_init(self, template_string, origin, name)
    self.origin = origin
Template.__init__ = new_template_init

class TemplateMiddleware:
    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and request.REQUEST.has_key('template'):
            self.time_started = time.time()
            self.templates_used = []
            self.contexts_used = []
        
            if not hasattr(self, 'loghandler'):
                self.loghandler = BufferingHandler(1000) # Create and a handler
                logging.getLogger('').addHandler(self.loghandler)
            else:
                self.loghandler.flush() # Empty it of all messages
        
            template_rendered.connect(
                self._storeRenderedTemplates
            )
    
    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and request.REQUEST.has_key('template'):
            templates = [
                (t.name, t.origin and t.origin.name or 'No origin')
                for t in self.templates_used
            ]

            template_context = Context({
                'server_time': time.time() - self.time_started,
                'templates': templates,
                'template_dirs': settings.TEMPLATE_DIRS,
            })

            response.content = Template(TEMPLATE).render(template_context)            

        return response
    
    def _storeRenderedTemplates(self, signal, sender, template, context, **kwargs):
        self.templates_used.append(template)
        self.contexts_used.append(context)