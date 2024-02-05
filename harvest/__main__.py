from configuration import load_configuration_files, load_logger
from cache import HarvestCacheConnection, HarvestCacheHeartBeatThread
from flask import Flask, jsonify, Response

# load the configuration.yaml file
api_configuration = load_configuration_files()

# startup the logging system
logger = load_logger(**api_configuration.get('logging', {}))

# connect to backend database
cache = HarvestCacheConnection(**api_configuration['cache']['connection'])

# activate the HeartBeatThread
HarvestCacheHeartBeatThread(cache=cache, version=api_configuration['version'])

# define the application
app = Flask(__name__)


@app.route('/jobs/start', methods=['PUT'])
def jobs_start(service: str, service_type: str, account: str, region: str):
    pass


@app.route('/jobs/stop', methods=['PUT'])
def jobs_stop(*job_identifiers: str):
    pass


@app.route('/jobs/status', methods=['GET'])
def jobs_status(*job_identifiers: str):
    pass


@app.route('/cache/credentials/update', methods=['PUT'])
def update_db_credentials(host: str, port: int, username: str, password: str, secrets_manager_secret_name: str, **kwargs):
    api_configuration['cache'] = kwargs
    # TODO: drop existing connections and reopen using this configuration


if __name__ == '__main__':
    app.run(**api_configuration.get('data-collector-aws'))
