from flask import (
    Flask, abort, render_template, flash, redirect, request, url_for,
    render_template_string, jsonify
)
from flask.ext import pymongo, bootstrap
from flask.ext.login import (
    LoginManager, login_user, login_required, UserMixin,
    logout_user, current_user, fresh_login_required
)
import wtforms
from flask_wtf import Form
import gridfs
import paramiko
import bson
import zmq

app = Flask(__name__)
mongo = pymongo.PyMongo(app)

login_manager = LoginManager()
login_manager.init_app(app)

bootstrap = bootstrap.Bootstrap()
bootstrap.init_app(app)


class LoginForm(Form):
    user = wtforms.StringField()
    password = wtforms.PasswordField()
    submit = wtforms.SubmitField()


@login_manager.user_loader
def load_user(userid):
    if userid == u'adr':
        user = UserMixin()
        user.id = userid
        return user
    return None


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = load_user(form.user.data)
        if user is None:
            abort(401)
        login_user(user)
        flash("Logged in successfully.", "alert-success")
        return redirect(request.args.get("next") or url_for("index"))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route('/workflows')
@login_required
def list_workflows():
    workflows = mongo.db.workflows.find({})
    return render_template('workflows.html', workflows=workflows)


@app.route('/running')
@login_required
def running():
    running = mongo.db.running.find()  # TODO {'user': current_user.id})
    running = list(running)
    return render_template('running.html', running=running)


@app.route('/running/<id>')
@login_required
def running_workflow(id):
    job = mongo.db.running.find_one({'_id': bson.ObjectId(id)})
    if job is None:
        abort(404)
    if 'wrkflw_id' in job:
        workflow = mongo.db.workflows.find_one({'_id': job['wrkflw_id']})
    else:
        workflow = None
    return render_template('running_workflow.html', job=job, meta=workflow)


@app.route('/workflows/<wfname>/<version>', methods=['GET'])
@login_required
def workflow(wfname, version):
    workflow = mongo.db.workflows.find_one(
        {'name': wfname, 'version': version}
    )
    workflow['_id'] = str(workflow['_id'])
    if workflow is None:
        abort(404)
    fs = gridfs.GridFS(mongo.db, collection="workflows")
    js = fs.get(workflow['_files']['webview']).read()
    return render_template(
        "workflow.html",
        meta={k: v for k, v in workflow.items() if k != '_files'},
        workflow_js=js.decode()
    )


@app.route('/submit/<wfname>/<version>', methods=['POST'])
@fresh_login_required
def start_workflow(wfname, version):
    workflow = mongo.db.workflows.find_one(
        {'name': wfname, 'version': version}
    )
    if workflow is None:
        abort(404)
    data = request.json
    if data is None:
        abort(415)
    try:
        jobid = execute_workflow(user=current_user, data=request.data,
                                 meta=workflow)
    except Exception as e:
        raise e
        return jsonify({"error": str(e)}), 501
    return jsonify({"jobid": jobid})  # TODO check CSRF!!


def execute_workflow(user, data, meta):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(hostname=app.config['CLUSTER_FRONTEND'],
                   username=user.id,
                   timeout=1)

    command = '{} --db={} --workflow-dir={} --workdir={} {}'.format(
        app.config['WORKFLOW_BOOTSTRAP_PATH'],
        app.config['DB_ZEROMQ'],
        app.config['WORKFLOW_DIR'],
        app.config['WORKDIR'],
        meta['name']
    )
    print(command)
    _, stdout, stderr = client.exec_command(command, timeout=5)
    jobid = stdout.readline().strip()
    print(jobid)
    print(stderr.read())
    return jobid


app.secret_key = 'hi_TODO_TODO'  # TODO
app.config['BOOTSTRAP_CDN_FORCE_SSL'] = True
app.config['CLUSTER_FRONTEND'] = 'localhost'
app.config['DB_ZEROMQ'] = 'tcp://127.0.0.1:6001'
app.config['WORKFLOW_BOOTSTRAP_PATH'] = (
    '/home/adr/git/QBiC/flask_test/snakeflow/utils/bootstrap_workflow'
)
app.config['WORKFLOW_DIR'] = (
    '/home/adr/git/QBiC/flask_test/workflows'
)
app.config['WORKDIR'] = '/home/adr/git/QBiC/flask_test/workdir'

if __name__ == '__main__':
    app.run(debug=True)
