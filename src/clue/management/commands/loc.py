import os
import commands
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.template import Template, Context
from django.conf import settings

try:
    # initialise the template engine
    settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)
except RuntimeError:
    pass

# set up some empty variables
file_list = []
test_list = []
file_loc = []
test_loc = []

# template for html output
TEMPLATE = """
<pre>
-----------------------------------
Lines of test code    {{test_code}}
Lines of app code     {{app_code}}
-----------------------------------
Code to test ratio    {{ratio}}
-----------------------------------
</pre>
"""

def parse_directory(dummy, dirr, file_list):
    # loop through all the files in the directory
    for child in file_list:
        # filter out everything that isn't a python file
        # this includes things like .svn files
        if '.py' == os.path.splitext(child)[1] and os.path.isfile(dirr+'/'+child):
            file_name = dirr+'/'+child
            # check to see if we are dealing with a test
            # we do this by looking for content in a tests directory
            # or called tests.py
            if dirr.split("/")[-1] == "tests" or child == "tests.py":
                # build a dictionary of test files
                # currently not used
                test_list.append(file_name)
                print file_name
                
                # calculate the number of lines of code
                # using the python_count command from sloccount
                loc = commands.getoutput("python_count " + file_name).split(' ')[0]
                # add the lines of code metric to the dict
                test_loc.append(float(loc))
            else:
                # we are dealing with other code
                file_list.append(file_name)
                print file_name
                # again calculate the lines of code using sloccount
                loc = commands.getoutput("python_count " + file_name).split(' ')[0]
                file_loc.append(float(loc))

def calculate_lines_of_code(directory, output="command"):
    # parse the directory passed on the command line
    os.path.walk(directory, parse_directory, 3)
    
    # if we asked for html
    if output == "html":
        # set context variables for template
        template_context = Context({
            'test_code': str(int(sum(test_loc))),
            'app_code': str(int(sum(file_loc))),
            'ratio': "1:" + str(round(sum(test_loc)/sum(file_loc),2))
        })
        # render template to string
        content = Template(TEMPLATE).render(template_context) 
        print content           
        
    # otherwise allways output the text
    else:
        # print output
        print "-------------------------------"
        print "Lines of test code     " + str(int(sum(test_loc)))
        print "Lines of app code      " + str(int(sum(file_loc)))
        print "-------------------------------"
        print "Code to test ratio     1:" + str(round(sum(test_loc)/sum(file_loc),2))
        print "-------------------------------"

class Command(BaseCommand):
    help = """Calculates the lines of code to lines of test code metric."""
        
    def handle(self, *args, **options):
        calculate_lines_of_code(settings.SITE_ROOT)