#!/usr/bin/env python
"""HtmlValidatorMiddleware for Django

See http://bstpierre.org/Projects/HtmlValidatorMiddleware

Required: Python 2.4 or later
Required: validate, the  Offline HTMLHelp.com Validator (or equivalent)
"""

__version__ = "1.1"
__license__ = """Copyright (c) 2007, Brian St. Pierre, All rights reserved.

Permission to use, copy, modify, and distribute this software and
its documentation for any purpose, without fee, and without a written
agreement is hereby granted, provided that the above copyright notice
and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS,
ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF
THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE.  THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS"
BASIS, AND THE AUTHOR HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT,
UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

__author__ = "Brian St. Pierre <http://bstpierre.org/>"

import math
from subprocess import *

from django.utils.html import escape
from django.http import HttpResponseServerError
from django.template import Context, Template
from django.conf import settings

# Just drop this middleware into your project, include it in your
# settings file (near the end, but before gzip), and any time a page
# does not validate, this middleware will send back a 500 error page
# containing the output from `validate` and the html source annotated
# with line numbers.
#
# This does not put anything into your database, it just squawks if
# you get a validation error.

# Customize this template if you want to.
ERROR_MESSAGE_TEMPLATE = '''
{% if error_message %}
<pre>
{{ error_message }}
</pre>
{% endif %}

<pre>
{{ escaped_source|safe }}
</pre>
'''
                
class HtmlValidatorMiddleware:
    def escaped_source(self, content):
        '''Return the given content with html escaped and line
        numbers in the left margin.'''

        # This is overkill, but it's nice to know that no matter how
        # long the content is, we'll have enough leading zeros so that
        # all of the numbers line up!
        lines = content.split('\n')
        format = '%%0%dd: %%s\n' % int(math.ceil(math.log(len(lines), 10)))

        output = ''
        n = 1
        for line in lines:
            output += format % (n, escape(line))
            n += 1
        return output
    
    def process_response(self, request, response):
        
        if (settings.DEBUG or request.user.is_superuser) and request.REQUEST.has_key('validate'):
            # Don't validate error pages.
            # Don't try to validate if it isn't html.
            if (response.status_code != 200 or
                response['Content-Type'] != 'text/html; charset=utf-8'):
                return response
        
            p = Popen(['validate'], stdin=PIPE, stdout=PIPE)
            p.stdin.write(response.content)
            p.stdin.close()
            output = p.stdout.read()


            ## The output is invalid! Modify the response to include
            ## the error message(s) and the escaped source.
            t = Template(ERROR_MESSAGE_TEMPLATE)
            c = Context({
                'error_message': output,
                'escaped_source': self.escaped_source(response.content),
                })

            error_response = HttpResponseServerError(t.render(c),
                                                     mimetype='text/html')
            return error_response
                
        return response