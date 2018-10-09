import flask
import json
from lib.files import get_download_data

@authenticate
def download_tasks():
    """Download multiple file base on tasks
    ---
    tags:
     - tasks

    parameters:
      - name: tasks
        in: formData
        type: string
        description: "a couple of tasks information you want to download like json bodies in a array and which should be encoded by json"
        example:
          [{
            "tid": "d7f13de3-7e0b-481f-b025-1faa6df9d764",
            "condition": {
              "type": "include",
              "fids": ["3eb8bfe1-b967-4c37-bc62-48a68b58308d"]
            }
          }]
      - name: include_source
        in: formData
        type: boolean
        default: true
        description: contain source data or not
    responses:
      200:
        description: "connection: Keep-Alive content-disposition: attachment; filename='download.zip'"
      400:
        schema:
          $ref: "#/definitions/errors"
        examples:
          invalidated argument:
            {
                "errors": [{
                    "code": "20003",
                    "data": "a0c4354b-058d-40b7-9bd6-0556515b23fd",
                    "message": "Argument is not a valid value"
                }]
            }
          missing arguments:
            {
                "errors": [{
                    "code": "20001",
                    "data": "tasks",
                    "message": "Missing required parameter in the JSON body, parameter: 'tasks'"
                }]
            }
      401:
        schema:
          $ref: "#/definitions/errors"
        examples:
          sid not found:
            {
                "errors": [{
                    "code": "31001",
                    "message": "SID not found"
                }]
            }
          invalid sid value:
            {
                "errors": [{
                    "code": "31002",
                    "message": "SID invalid or expired"
                }]
            }
      500:
        schema:
          $ref: "#/definitions/errors"
        examples:
          parse smb.conf error:
            {
                "errors": [{
                    "code": "54001",
                    "message": "Parse SmbConfig error"
                }]
            }
          connect DB error:
            {
                "errors": [{
                    "code": "40001",
                    "message": "Can't connect to DB server"
                }]
            }
          query sql fail:
            {
                "errors": [{
                    "code": "40003",
                    "message": "Sql query fail"
                }]
            }
          I/O error:
            {
                "errors": [{
                    "code": "12001",
                    "message": "file I/O error"
                }]
            }
          unknown error:
            {
                "errors": [{
                    "code": "10999",
                    "message": "Unknown error"
                }]
            }
    """
    parser = RequestParser()
    parser.add_argument("tasks", type=inputs.string, location="form", required=True)
    parser.add_argument("include_source", type=inputs.boolean, location="form", default=True)
    args = parser.parse_args()

    try:
        task_list = json.loads(args.tasks)
        tasks = inputs.tasks(convert_unicode_to_str(task_list))
    except Exception:
        raise ArgumentError(code=err.REQUEST_ARG_NOT_VALID, data="tasks")

    # get download data information
    try:
        download_data = get_download_data(tasks, flask.g.userid, flask.g.username, flask.g.usertype, args.include_source)

        # if success , error will be None
        if not download_data["error"]:
            return send_iter_file(download_data["iter_data"], app_const.ZIP_NAME)
        elif download_data["error"] == err.REQUEST_ARG_NOT_VALID:
            raise ArgumentError(code=err.REQUEST_ARG_NOT_VALID, data="tasks")
        else:
            raise ApiError(code=err.DOWNLOAD_ERROR)
    except ParseSmbConfError:
        raise ApiError(code=err.SMB_CONF_PARSE_ERROR, http_status=500)
    except ConnectionError:
        raise ApiError(code=err.DB_CONNECTION_ERROR, http_status=500)
    except PostgresError:
        raise ApiError(code=err.DB_QUERY_FAIL, http_status=500)
    except IOError:
        raise ApiError(code=err.IO_ERROR, http_status=500)