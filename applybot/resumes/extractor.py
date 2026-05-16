try:
    from config.personals import *
except ImportError:
    pass
try:
    from config.questions import default_resume_path
except ImportError:
    default_resume_path = ""




