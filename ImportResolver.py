import os
import sys
import shutil
import stat
import re
import logging
import logging.handlers

def logger():
    return logging.getLogger('importresolver_logger')

def init_logger(log_level = logging.DEBUG, log_format = None, log_to_console = True, log_to_file = False, log_file = None):
    # create logger with 'spam_application'
    logger().setLevel(log_level)
    formatter = None
    if log_format <> None: formatter = logging.Formatter(log_format)
    # create file handler
    if log_to_file and log_file:
        fh = logging.handlers.TimedRotatingFileHandler(filename = log_file, when = 'midnight', interval = 1, utc = True, backupCount = 7)
        fh.setLevel(log_level)
        if formatter != None:
            fh.setFormatter(formatter)
        logger().addHandler(fh)
    # create console handler
    if log_to_console:
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        if formatter != None:
            ch.setFormatter(formatter)
        logger().addHandler(ch)

def get_cwd():
    cwd = os.path.abspath(os.path.dirname(__file__))
    if hasattr(sys, 'frozen'):
        cwd = os.path.abspath(os.path.dirname(sys.executable))
    return cwd

def copy_to_file(src, dest):
    output_dir = os.path.dirname(dest)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if os.path.exists(dest):
        os.chmod(dest, stat.S_IWRITE|stat.S_IREAD)
        os.remove(dest)
    shutil.copyfile(src, dest)
    os.chmod(dest, stat.S_IWRITE|stat.S_IREAD)

def move_to_file(src, dest):
    if os.path.exists(src):
        copy_to_file(src, dest)
        if not os.access(src, os.W_OK):
            os.chmod(src, stat.S_IWRITE|stat.S_IREAD)
        os.remove(src)

def replace_old_file(root, subdir, new_file, old_file, need_print):
    old_file_path = os.path.join(root, old_file)
    if os.path.exists(old_file_path):
        new_file_path = os.path.join(root, new_file)
        if need_print:
            sys.stdout.write(subdir + '/' + new_file + '  ------>  ' + old_file + '\n')
        logger().info(subdir + '/' + new_file + '  ------>  ' + old_file)
        move_to_file(new_file_path, old_file_path)

class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()

class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

getch = _Getch()

def query_yes_no(question, default="yes"):
    valid = {"yes": True,
             "y": True,
             "ye": True,
             "no": False,
             "n": False}
    sys.stdout.write(question + '\n')
    while True:
        #choice = raw_input().lower()
        choice = getch()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("\nPlease respond with 'y' or 'n':\n")

def try_replace_old_files(root, subdir, file_without_ext, file_without_num):
    similiar_files = []
    for f in os.listdir(root):
        if os.path.isfile(os.path.join(root, f)):
            if f.startswith(file_without_num):
                f_without_ext = os.path.splitext(f)[0]
                f_without_num = re.sub('\d+$', '', f_without_ext)
                num_match = re.search('\d+$', f_without_ext)
                if num_match is not None:
                    if file_without_num + num_match.group() == f_without_ext:
                        similiar_files.append(f)

    file_count = len(similiar_files)
    if file_count > 1:
        similiar_files.sort()
        file_index = file_count
        for f in reversed(similiar_files):
            if file_index == 1:
                break
            f_without_ext, ext = os.path.splitext(f)
            f_without_num = re.sub('\d+$', '', f_without_ext)
            num_match = re.search('\d+$', f_without_ext)
            old_file = f_without_num + str(int(num_match.group()) - 1) + ext
            if os.path.exists(os.path.join(root, old_file)):
                if query_yes_no(subdir + '/' + f + '  ------>  ' + old_file + '  ? [y/n]:'):
                    replace_old_file(root, subdir, f, old_file, False)
            --file_index

if __name__ == '__main__':
    init_logger(log_level=logging.DEBUG, log_to_console=False, log_to_file=True, log_file='./ImportResolverLog.txt')

    cwd = get_cwd()

    for root, subdirs, files in os.walk(cwd):
        excludes = []
        subdir = root.replace(cwd, '.')
        subdir = subdir.replace('\\', '/')
        for f in files:
            if f.find(' 1') != -1:
                # Unity 5 plugin importing will just append ' 1' intead of overwrite if there is a same file
                old_file = f.replace(' 1', '')
                replace_old_file(root, subdir, f, old_file, True)
            else:
                # Unity 5 plugin importing will create new file by adding 1 for the exsiting file which has num suffix
                file_without_ext = os.path.splitext(f)[0]
                num_match = re.search('\d+$', file_without_ext)
                if num_match is not None:
                    file_without_num = re.sub('\d+$', '', file_without_ext)
                    if file_without_num not in excludes:
                        try_replace_old_files(root, subdir, file_without_ext, file_without_num)
                        excludes.append(file_without_num)
