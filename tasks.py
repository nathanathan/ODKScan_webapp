import os
import sys, subprocess
APP_ROOT = os.path.dirname(__file__)

from ODKScan_webapp.models import FormImage

import celery

@celery.task
def process_image(id):
    obj = FormImage.objects.get(id=id)
    obj.status = 'w'
    obj.save()
    stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run',
                      os.path.dirname(obj.template.image.path) + '/',
                      obj.image.path,
                      obj.output_path
                      ],
        cwd=os.path.join(APP_ROOT,
                         'ODKScan-core'),
        #env={'LD_LIBRARY_PATH':'/usr/local/lib'}, #TODO: This could cause problems on other systems, document or fix
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT).communicate()
    print >>sys.stdout, stdoutdata
    obj.processing_log = stdoutdata
    json_path = os.path.join(obj.output_path, 'output.json')
    if os.path.exists(json_path):
        #process_json_output(json_path)#Not sure I need this.
        obj.status = 'p'
    else:
        obj.status = 'e'
    obj.save()