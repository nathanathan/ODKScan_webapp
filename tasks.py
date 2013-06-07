import os
import sys, subprocess
APP_ROOT = os.path.dirname(__file__)
from ODKScan_webapp.models import FormImage
import celery
import json

@celery.task
def process_image(id):
    """
    Process the form image with the given id.
    """
    # I can't seem to get the celery logger to work...
    logger = process_image.get_logger(logfile='tasks.log')
    logger.warning("test")
    
    obj = FormImage.objects.get(id=id)
    #w for working, because p for processing is already taken.
    obj.status = 'w'
    obj.save()
    
    #Create ouput directory for the segments:
    try:
        segment_dir = os.path.join(obj.output_path, "segments")
        if not os.path.exists(segment_dir):
            os.mkdir(segment_dir)
    except:
        obj.status = 'e'
        obj.save()
        #TODO: Put an error message somewhere
        return
    
    config_string = json.dumps({
        "inputImage" : obj.image.path,
        "outputDirectory" : obj.output_path,
        "alignForm" : True,
        "processForm" : True,
        "detectOrientation" : True,
        "templatePath" : os.path.dirname(obj.template.image.path) + '/',
        "trainingDataDirectory" : "assets/training_examples/"
    })
    
    #TODO: Make sure the app is configured correctly and ODKScan.run exisits.
    
    stdoutdata, stderrdata = subprocess.Popen(['./ODKScan.run', config_string],
        cwd=os.path.join(APP_ROOT,
                         'ODKScan-core'),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT).communicate()
    try:
        # I'm in trouble if the splitting string ever ends up in
        # the JSON result or processing log.
        log, result_text = stdoutdata.split("<======= RESULT =======>")
        obj.processing_log = stdoutdata
        result = json.loads(result_text)
        if "errorMessage" in result:
            obj.status = 'e'
        else:
            obj.status = 'p'
    except:
        obj.status = 'e'
    obj.save()
