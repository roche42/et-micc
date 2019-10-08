# -*- coding: utf-8 -*-
"""
logging helpers for micc.py
"""

import sys
from contextlib import contextmanager
import logging
from datetime import datetime

def verbosity_to_loglevel(verbosity):
    """
    :param int verbosity:
    """
    if verbosity==0:
        return logging.CRITICAL
    elif verbosity==1:
        return logging.INFO
    else:
        return logging.DEBUG


def static_vars(**kwargs):
    """
    Add static variables to a method.
    """
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


# Use static vare to implement a singleton
@static_vars(the_logger=None)
def get_micc_logger(global_options): 
    """
    Set up and store a micc logger that writes to the console (taking verbosity 
    into account) and to a log file ``micc.log``.
    
    :param types.SimpleNamespace global_options: namespace object with options 
        accepted by (almost) all micc commands.
    :returns: a logging.Logger object.
    """
    
    if not get_micc_logger.the_logger is None:
        # verify that the current logger is for the current project directory
        # (When running pytest, micc commands are run in several different
        # project directories created on the fly. the micc_logger must adjust
        # to this situation and log to a micc.log file in the project directory.
        current_logfile = get_micc_logger.the_logger.logfile
        current_project_path = global_options.project_path
        if not current_logfile.parent == current_project_path:
            get_micc_logger.the_logger = None
            
    if get_micc_logger.the_logger is None:
        
        if global_options.clear_log:
            logfile = global_options.project_path / 'micc.log'
            if logfile.exists():
                logfile.unlink()
            else: 
                global_options.clear_log = False
                
        # create a new logger object that will write to micc.log 
        # in the current project directory
        p = global_options.project_path / 'micc.log'
        get_micc_logger.the_logger = create_logger(p)
        get_micc_logger.the_logger.logfile = p
        if global_options.verbosity>2:
            print(f"micc_logger.logfile = {get_micc_logger.the_logger.logfile}")
            
    # set the log level from the verbosity
    get_micc_logger.the_logger.console_handler.setLevel(verbosity_to_loglevel(global_options.verbosity))

    if global_options.clear_log:
        global_options.clear_log = False
        get_micc_logger.the_logger.debug("The log file was cleared.")

    return get_micc_logger.the_logger


class IndentingLogger(logging.Logger):
    def __init__(self,name,level=logging.NOTSET):
        super().__init__(name,level)
        self._indent = ''
        self._stack = []
        
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        msg = msg.strip()
        levelname = logging.getLevelName(level)
        w = (10-len(levelname)) * ' '
        if self._indent:
            msg = w + self._indent + msg.replace('\n','\n ' + create_logger.base_indent*' ' + self._indent)
        super()._log(level, msg, args, exc_info, extra)
            
    def indent(self,n=4):
        self._indent += n*' '
        self._stack.append(n)
            
    def dedent(self):
        if self._stack:
            n = self._stack.pop()
            length = len(self._indent) - n
            self._indent = self._indent[0:length]


def log_datetime():
    now = datetime.now()
    get_micc_logger.the_logger.debug(str(now))


@static_vars(base_indent=8)
def create_logger(filepath,filemode='a'):
    """
    create a logging.Logger object with a 
    
    * console handler
    * file handler, writing to file ``filename``
    """
    # create formatters and add it to the handlers
    format_string = f"[%(levelname)s] %(message)s"
    console_formatter = logging.Formatter(format_string)
    logfile_formatter = logging.Formatter(format_string)
    # create and add a console handler 
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(1)
    
    # create and add a logfile handler
    logfile_handler = logging.FileHandler(filepath,mode=filemode)
    logfile_handler.setFormatter(logfile_formatter) 
    logfile_handler.setLevel(logging.DEBUG)
            
    # set custom logger class
    logging.setLoggerClass(IndentingLogger)

    # create logger for micc
    logger = logging.getLogger(filepath.name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logfile_handler)
    logger.addHandler(console_handler)
    
    # add the handlers as a member, so we can still modify them on the fly.
    logger.logfile_handler = logfile_handler
    logger.console_handler = console_handler
    
    return logger


@contextmanager
def log(logfun=None, begin_msg='doing', end_msg='done.'):
    """
    Print a start and stop message when executing a task.

    :param logfun: function that writes  e.g. ``logging.info`
    :param str begin_msg: print this before body is executed
    :param str end_msg: print this after body is executed
    :param singleline: generates a single line execution trace as in
        `<begin_msg> ... <end_msg>`. Calling print2stderr may obfuscate this.
    """
    if logfun:
        logfun(begin_msg)
        try:
            logfun.__self__.indent()
            is_logger = True
        except AttributeError:
            is_logger = False
    yield
    if logfun:
        if is_logger:
            logfun.__self__.dedent()
        logfun(end_msg)

@contextmanager
def logtime(global_options=None):
    """
    Print a start and stop message when executing a task.

    :param logfun: function that writes  e.g. ``logging.info`
    :param str begin_msg: print this before body is executed
    :param str end_msg: print this after body is executed
    :param singleline: generates a single line execution trace as in
        `<begin_msg> ... <end_msg>`. Calling print2stderr may obfuscate this.
    """
    if global_options is None:
        logfun = get_micc_logger.the_logger.debug
    else:
        logfun = get_micc_logger(global_options).debug
    start = datetime.now()
    logfun(f"start = {start}")
    logfun.__self__.indent()

    yield
    logfun.__self__.dedent()
    stop = datetime.now()
    logfun(f"stop  = {stop}")
    spent = stop - start
    logfun(f"spent = {spent}")
    

