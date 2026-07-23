import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/trungbao/CYBER/cyberruner-main/install/cyberrunner_state_estimation'
