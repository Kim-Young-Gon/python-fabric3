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
deploy_folder = '/home/{}/{}/{}'.format(env.user, DEPLOY_PATH, PROJECT_NAME)


# _로 시작하지 않는 함수들은 fab new_server 처럼 명령줄에서 바로 실행이 가능합니다.
def deploy():
    _get_latest_source('prod')
    _restart_uwsgi('prod')


# 테스트 배포
def deploy_test():
    _get_latest_source('dev')
    _restart_uwsgi('dev')


# deploy 디렉토리에서 파일을 복사한다.
def _get_latest_source(type_value):
    if type_value == 'prod':
        project_folder = '/home/{}/anaconda3/envs/{}/script'.format(env.user, PROJECT_NAME)
    else:
        project_folder = '/home/{}/anaconda3/envs/{}/script-test'.format(env.user, PROJECT_NAME)
    if not exists(project_folder):
        run('mkdir -p %s' % project_folder)
    if exists(deploy_folder):
        run('cp -r %s/* %s' % (deploy_folder, project_folder))
        if type_value == 'prod':
            run('rm -f %s/%s-test.ini' % (project_folder, PROJECT_NAME))
        else:
            run('rm -f %s/%s.ini' % (project_folder, PROJECT_NAME))


# 마지막으로 uwsgi를 재시작합니다.
def _restart_uwsgi(type_value):
    if type_value == 'prod':
        sudo('systemctl restart uwsgi')
    else:
        sudo('systemctl restart uwsgi-test')

