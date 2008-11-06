import os
import commands

from django.core.management.base import BaseCommand
from django.conf import settings
from django.template import Template, Context

try:
    # initialise the template engine
    settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)
except RuntimeError:
    # template engine already configured
    pass

# set up some empty variables
FILE_LIST = []
TEST_LIST = []
FILE_LOC = []
TEST_LOC = []

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
        if '.py' == os.path.splitext(child)[1] \
            and os.path.isfile(dirr+'/'+child):
            file_name = dirr+'/'+child
            # check to see if we are dealing with a test
            # we do this by looking for content in a tests directory
            # or called tests.py
            if dirr.split("/")[-1] == "tests" or child == "tests.py":
                # build a dictionary of test files
                # currently not used
                TEST_LIST.append(file_name)
                print file_name
                
                # calculate the number of lines of code
                # using the python_count command from sloccount
                loc = commands.getoutput("python_count " 
                    + file_name).split(' ')[0]
                # add the lines of code metric to the dict
                TEST_LOC.append(float(loc))
            else:
                # we are dealing with other code
                FILE_LIST.append(file_name)
                print file_name
                # again calculate the lines of code using sloccount
                loc = commands.getoutput("python_count " 
                    + file_name).split(' ')[0]
                FILE_LOC.append(float(loc))

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
        loc_to_test_code = str(round(sum(TEST_LOC)/sum(FILE_LOC), 2))
        
        print "-------------------------------"
        print "Lines of test code     " + str(int(sum(TEST_LOC)))
        print "Lines of app code      " + str(int(sum(FILE_LOC)))
        print "-------------------------------"
        print "Code to test ratio     1:" + loc_to_test_code
        print "-------------------------------"

class Command(BaseCommand):
    help = """Calculates the lines of code to lines of test code metric."""
        
    def handle(self, *args, **options):
        calculate_lines_of_code(settings.SITE_ROOT)