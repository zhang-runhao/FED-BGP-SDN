import subprocess

subprocess.call('cmd /k "python .\GlobalController.py --config .\config\globalConfig.json"', shell=True)
subprocess.call('cmd /k "python .\LocalController.py --config .\config\asConfig1.json"', shell=True)
subprocess.call('cmd /k "python .\LocalController.py --config .\config\asConfig2.json"', shell=True)