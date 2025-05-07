from CloudHarvestCoreTasks.blueprints import HarvestApiBlueprint
from flask import jsonify


test_pb = HarvestApiBlueprint(
    'test_bp', __name__
)


@test_pb.route('/test/aws')
def test_route():
    return jsonify('Successful Test Route')

