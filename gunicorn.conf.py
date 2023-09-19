import os
import pathlib

template_root = os.path.join(os.getcwd(), "templates")
template_list = []

for path, subdirs, files in os.walk(template_root):
    for name in files:
        template_list.append(str(pathlib.PurePath(path, name)))

bind = "0.0.0.0:8000"
reload = True
reload_extra_files = template_list
