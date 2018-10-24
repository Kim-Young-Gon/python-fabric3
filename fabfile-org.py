from fabric.contrib.files import append, exists, sed, put
from fabric.api import env, local, run, sudo
import os
import json

# 현재 fabfile.py가 있는 폴더의 경로
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# deploy.json이라는 파일을 열어 아래의 변수들에 담아줍니다.
envs = json.load(open(os.path.join(PROJECT_DIR, "deploy.json")))

PROJECT_NAME = envs['PROJECT_NAME']
REMOTE_HOST = envs['REMOTE_HOST']
REMOTE_HOST_SSH = envs['REMOTE_HOST_SSH']
REMOTE_USER = envs['REMOTE_USER']
REMOTE_PASSWORD = envs['REMOTE_PASSWORD']
DEPLOY_PATH = envs['DEPLOY_PATH']

# SSH에 접속할 유저를 지정하고,
env.user = REMOTE_USER
# SSH로 접속할 서버주소를 넣어주고,
env.hosts = [
    REMOTE_HOST_SSH,
]
env.password = REMOTE_PASSWORD
# 원격 서버중 어디에 프로젝트를 저장할지 지정해준 뒤,
project_folder = '/home/{}/{}'.format(env.user, PROJECT_NAME)
deploy_folder = '/home/{}/{}'.format(env.user, DEPLOY_PATH)


# _로 시작하지 않는 함수들은 fab new_server 처럼 명령줄에서 바로 실행이 가능합니다.
def new_server():
    setup()
    deploy()


def setup():
    _make_virtualenv()


def deploy():
    _get_latest_source()
    _update_virtualenv()
    _make_virtualhost()
    _grant_apache2()
    _restart_apache2()


# virtualenv와 virtualenvwrapper를 받아 설정합니다.
def _make_virtualenv():
    if not exists('~/.virtualenvs'):
        script = '''"# python virtualenv settings
export WORKON_HOME=~/.virtualenvs
export VIRTUALENVWRAPPER_PYTHON="$(command \which python3)" # location of python3
source /usr/bin/virtualenvwrapper.sh"'''
    run('mkdir ~/.virtualenvs')
    sudo('pip3 install virtualenv virtualenvwrapper')
    run('echo {} >> ~/.bashrc'.format(script))
    # 아파치에서 계정 디렉토리에 접근 할 수 있도록 권한 설정
    sudo('chmod 755 /home/{}'.format(REMOTE_USER))


# deploy 디렉토리에서 파일을 복사한다.
def _get_latest_source():
    if not exists(project_folder):
        run('mkdir -p %s' % project_folder)
    else:
        sudo('rm -rf {}'.format(project_folder))
        run('mkdir -p %s' % project_folder)
    if exists(deploy_folder):
        run('cp -r %s/* %s' % (deploy_folder, project_folder))


# requirements.txt를 통해 pip 패키지를 virtualenv에 설치해줍니다.
def _update_virtualenv():
    virtualenv_folder = project_folder + '/../.virtualenvs/{}'.format(PROJECT_NAME)
    if not exists(virtualenv_folder + '/bin/pip'):
        run('cd /home/%s/.virtualenvs && virtualenv %s' % (env.user, PROJECT_NAME))
    run('%s/bin/pip3 install -r %s/requirements.txt' % (virtualenv_folder, project_folder))
    # 가상환경을 아파치에서 접근 할 수 있도록 권한 설정
    run('chcon -R --type=httpd_sys_content_t %s' % virtualenv_folder)


# Apache2의 Virtualhost를 설정해 줍니다.
# 이 부분에서 wsgi.py와의 통신, 그리고 virtualenv 내의 파이썬 경로를 지정해 줍니다.
def _make_virtualhost():
    script = """'<VirtualHost *:80>
    ServerName {servername}
    <Directory /home/{username}/{project_name}>
        Require all granted
    </Directory>
    WSGIDaemonProcess {project_name} python-home=/home/{username}/.virtualenvs/{project_name} python-path=/home/{username}/{project_name}
    WSGIProcessGroup {project_name}
    WSGIScriptAlias / /home/{username}/{project_name}/wsgi.py
</VirtualHost>'""".format(
        username=REMOTE_USER,
        project_name=PROJECT_NAME,
        servername=REMOTE_HOST,
    )
    sudo('echo {} > /etc/httpd/conf.d/{}.conf'.format(script, PROJECT_NAME))


# Apache2가 프로젝트 파일을 읽을 수 있도록 권한을 부여합니다.
def _grant_apache2():
    sudo('chmod -R a+r {}/*'.format(project_folder))
    run('chcon -R --type=httpd_sys_content_t %s' % project_folder)


# 마지막으로 Apache2를 재시작합니다.
def _restart_apache2():
    sudo('systemctl restart httpd.service')