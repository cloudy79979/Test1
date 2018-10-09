# -*- coding: utf-8 -*-

# std
import logging
import os
import uuid
import shutil

# app
from .const.app import LOGGER_NAME
from lib.const.err import REQUEST_ARG_VALUE_ERROR, DOWNLOAD_ERROR
from lib.dao.files import get_files_by_tid
from lib.dao.tasks import get_owned_tids
from lib.dao import create_db_client
from lib.const.app import APP_PATH, OCR_MISSING_MESSAGE
from packages.conf.smb_conf import ParseSmbConfError
from packages.perm.nas_perm import NasPermChecker
from packages.qts_path import cast2real_path

logger = logging.getLogger(LOGGER_NAME).getChild(__name__)

def get_download_data(task_list, userid, username, usertype, include_source):
    """ Get download data with permission

    We have to check path permission and get real file path here,

    so initializing NasPermChecker and using cast2real_path() function which will throw ParseSmbConfError exception

    in lower-level function.

    :param task_list: task list
           E.g
           [
             {
               "condition": {
               "fids": [
                 "03642a1a-283e-4172-a4a1-bc2746624a3b"
               ],
               "type": "include"
               },
               "tid": "a0c4354b-058d-40b7-9bd6-0556515b23fd"
             }
           ]
    :param userid: uid
    :param username: username. E.g, "admin"
    :param usertype: user type. E.g, "local", "domain"
    :param include_source: download file with source or not. E.g, True
    :raises ParseSmbConfError:
        compose_download_files() will throw ParseSmbConfError exception from low-level function, because parsing smb.conf error
    :return: {"iter_data": data streaming, "error": None}
    """
    files = get_files_by_tasks(task_list, username)

    # get iter data
    return compose_download_files(files, userid, username, usertype, include_source)


def get_files_by_tasks(task_list, username):
    """ checking tid and fid owner
    return list contains files information
    """
    client = create_db_client()
    file_list = []

    # check tids owner
    tids = [task["tid"] for task in task_list]
    pass_tids = get_owned_tids(client, username, tids=tids)
    for task in task_list:
        if task["tid"] in pass_tids:
            if "condition" not in task:
                files = get_files_by_tid(client, tid=task["tid"], check_finish=True)
                file_list.extend(files)
            else:
                fids = task["condition"]["fids"]
                if len(fids) != 0:
                    # get files
                    files = get_files_by_tid(client, tid=task["tid"], condition_type=task["condition"]["type"], condition_values=fids, check_finish=True)
                    file_list.extend(files)
    return file_list


def content(iter_data):
    for chunk in iter_data:
        if chunk:
            yield chunk


def compose_download_files(files, userid, username, usertype, include_source):
    """ check single file or files to assign download name

    :raises ParseSmbConfError:
        1. check_duplicate() will throw ParseSmbConfError from low-level, because parsing smb.conf error
        2. _files_iter() will throw ParseSmbConfError from low-level, because parsing smb.conf error
    """

    # check file length
    if len(files) == 0:
        return {"iter_data": None, "error": REQUEST_ARG_VALUE_ERROR}

    # filter duplicate file
    allowed_files = check_duplicate(files, username, usertype)

    iter_data = _files_iter(allowed_files, userid, username, usertype, include_source)
    if not iter_data:
        return {"iter_data": None, "error": DOWNLOAD_ERROR}
    return {"iter_data": iter_data, "error": None}


def _get_physical_path(share_path, username, user_type):
    """ Convert share path real path

    This function will throw ParseSmbConfError to upper-level function

    :param share_path: NAS share path
    :param username: username E.g, "admin"
    :param user_type: user_type E.g, "local", "domain"
    :raises ParseSmbConfError:
        cast2real_path will call get_smbconfig() and error occur when get_smbconfig() parsing wrong format smb.conf
    :return: file real path
    """
    try:
        physical_path = cast2real_path(share_path=share_path, username=username, usertype=user_type)
    except ParseSmbConfError:
        logger.error("download task error, error: can't parse smb.conf correctly")
        raise
    except RuntimeError:
        physical_path = ""
    return physical_path


def check_duplicate(files, username, usertype):
    """ filter duplicate source file (different tid but same file) 

    :raises ParseSmbConfError:
        _get_physical_path() will throw ParseSmbConfError from low-level, because parsing smb.conf error
    """
    ocr_path_set = set()
    allowed_files = []
    for file_ in files:
        ocr_path = _get_physical_path(file_["ocr_path"], username, usertype)
        # check ocr file exist
        if ocr_path and ocr_path not in ocr_path_set:
            # add real path to files
            ocr_path_set.add(ocr_path)
            file_["ocr_real_path"] = ocr_path
            file_["source_real_path"] = _get_physical_path(file_["source_path"], username, usertype)
            allowed_files.append(file_)
    return allowed_files


def get_mapping_filename(files):
    """ mapping ocr_name and source_name 
    avoid mutiple same name in a folder
    """
    source_name_counts = {}  # Recored existed source name
    source_path_cache = set()  # Recored existed source path

    # add serial number for same source name, ex: /Public/a.jpg, /Downloads/a.jpg have same name 
    for file_ in files:
        # rename ocr_file
        file_name = file_["ocr_name"]
        source_name = file_["source_name"]
        source_path = file_["source_path"]

        # filter same source path, ex: /Public/a.jpg <-> a.txt, a.pdf
        if source_path not in source_path_cache:
            if source_name not in source_name_counts:
                source_name_counts[source_name] = 0
            else:
                source_name_counts[source_name] += 1
            source_path_cache.add(source_path)

        # mapping serial number to ocr file by source_name, ex: a(1).jpg <-> a(1).txt
        file_["ocr_name"] = rename_by_sequential_number(file_name, source_name_counts[source_name], file_["source_name"])
        file_["source_name"] = rename_by_sequential_number(source_name, source_name_counts[source_name])

        # check source file exist
        if not os.path.exists(file_["source_real_path"]):
            file_["ocr_name"] = rename_by_missing_source(file_["ocr_name"])
    return files        


def rename_by_sequential_number(file_name, number, sub_string=None):
    """ rename file by given sequential number
    :param file_name: rename target
    :param number: sequential_number
    :param sub_string: sub string in file_name
        if you want to give sequential number for sub string in filename    
    """
    if number != 0:
        if not sub_string:
            name, ext = os.path.splitext(file_name)
            file_name = "%s(%s)%s" % (name, number, ext)
        else:
            revised_sub_string = rename_by_sequential_number(sub_string, number)
            file_name = file_name.replace(sub_string, revised_sub_string)
    return file_name


def rename_by_missing_source(file_name):
    name, ext = os.path.splitext(file_name)
    file_name = "%s_%s%s" % (name, OCR_MISSING_MESSAGE, ext)
    return file_name


def gen_link_list(files, workspace_path, include_source):
    # create link list
    link_list = []
    source_real_path_set = set()
    for file_ in files:
        link_list.append({
            "ln_path": "%s/%s" % (workspace_path, file_["ocr_name"]),
            "real_path": file_["ocr_real_path"],
            "path": file_["ocr_path"]
        })
        if include_source:
            # filter duplicate source
            if file_["source_real_path"] not in source_real_path_set:
                source_real_path_set.add(file_["source_real_path"])
                link_list.append({
                    "ln_path": "%s/%s" % (workspace_path, file_["source_name"]),
                    "real_path": file_["source_real_path"],
                    "path": file_["source_path"]
                })
    return link_list


def _files_iter(files, userid, username, usertype, include_source):
    """ Get file streaming

    :raises ParseSmbConfError:
        1. Initializing NasPermChecker class will call get_smbconfig() in low-level function,
        and error occur when parsing wrong format smb.conf
        2. have_perm() method will call get_smbconfig() in low-level function,
        and error occur when parsing wrong format smb.conf

        This function will throw ParseSmbConfError to upper-level function
    """

    # Create soft links to make zip file
    workspace_path = "%s/tmp/%s" % (APP_PATH, str(uuid.uuid4()))
    file_list = "%s/%s" % (workspace_path, str(uuid.uuid4()))
    try:
        os.makedirs(workspace_path)

        # get mapping file name
        files = get_mapping_filename(files)

        # create link list
        link_list = gen_link_list(files, workspace_path, include_source)

        # check permission
        perm_checker = NasPermChecker(uid=userid, username=username, usertype=usertype)

        #TODO if file missing abc(2).txt, may cause abc.txt abc(1).txt abc(3).txt
        with open(file_list, "w") as f:
            # link file to temp folder
            for link in link_list:
                if os.path.exists(link["real_path"]) and perm_checker.have_perm(link["path"]):
                    os.symlink(link["real_path"], link["ln_path"])
                    f.write(link["ln_path"] + "\n")

        if not os.path.getsize(file_list):
            return None
        command = "/bin/cat %s | /usr/local/sbin/zip -jq0@ -" % file_list
        output = os.popen(command)
        if output:
            def content():
                try:
                    data = output.read(4096)
                    while data:
                        yield data
                        data = output.read(4096)
                    output.close()
                finally:
                    shutil.rmtree(workspace_path)
            return content()
    except ParseSmbConfError:
        logger.error("download task error, error: can't parse smb.conf correctly")
        shutil.rmtree(workspace_path)
        raise
    except:
        shutil.rmtree(workspace_path)
