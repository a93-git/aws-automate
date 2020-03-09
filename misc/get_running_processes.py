""" Sample program to list all the running processes (Linux)  and services (Windows) on the current system

Uncomment the logging statements to enable it (if the system supports it)

The default log location depends on the environment (in AWS it is cloudwatch log groups)
"""

import os
#import logging
import subprocess

#logger = logging.getLogger()
#logger.setLevel(logging.DEBUG)

def get_running_process():
    """ Get a list of all the running processes/services on the current system"""
    try:
        if 'win' in os.sys.platform:
            command = 'Get-Service'
    #        logger.info("The platform is Windows")
    #        logger.info("Executing powershell command {0} to list all the processes".format(command))
            print("The platform is Windows")
            print("Executing powershell command {0} to list all the services".format(command))
            ret = subprocess.run(['powershell.exe', command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #        logger.info(ret.stdout.decode('utf-8'))
            print(ret.stdout.decode('utf-8'))
        elif 'linux' in os.sys.platform:
            command = '/bin/ps'
            option = '-ef'
    #        logger.info("The platform is Linux")
    #        logger.info("Executing shell command {0} to list all the processes".format(command))
            print("The platform is Linux")
            print("Executing shell command {0} to list all the processes".format(command))
            ret = subprocess.run([command, option], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #        logger.info(ret)
            print(ret.stdout.decode('utf-8'))
        else:
    #        logger.error("Error in running commands. No supported platforms found.")        
            print("Error in running commands. No supported platforms found.")
        return True
    except Exception as e:
    #    logger.info("Error in executing the script. Error message is:")
    #    logger.error(e)
        print("Error in executing the script. Error message is:")
        print(str(e))
        return False

if __name__ == '__main__':
    get_running_process()