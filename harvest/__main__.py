from configuration import load_configuration
from flask import Flask, jsonify, Response
from logging import getLogger

logger = getLogger('harvest')

# load the configuration.yaml file
configuration = load_configuration()

# define the application
app = Flask(__name__)


@app.route('/jobs/start', method='PUT')
def jobs_start(service: str, service_type: str, account: str, region: str):
    pass


@app.route('/jobs/stop', method='PUT')
def jobs_start(*job_identifiers: str):
    pass


@app.route('/jobs/status', method='GET')
def jobs_start(*job_identifiers: str):
    pass


@app.route('/cache/credentials/update', method='PUT')
def update_db_credentials(host: str, port: int, username: str, password: str, secrets_manager_secret_name: str, **kwargs):
    configuration['cache'] = kwargs
    # TODO: drop existing connections and reopen using this configuration


if __name__ == '__main__':
    app.run(**configuration.get('data-collector-aws'))
