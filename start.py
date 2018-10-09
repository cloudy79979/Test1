import flask
from resources.tasks import download_tasks
class SampleFlask(flask.Flask):
    # This part only for demo


# route
app.add_url_rule("/xxx/api/tasks/download", "download_tasks", download_tasks, methods=["POST"])


if __name__ == "__main__":
    app.run(debug=False, port=API_PORT)