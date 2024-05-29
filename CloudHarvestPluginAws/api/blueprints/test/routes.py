from api.blueprints.base import HarvestBlueprint
from flask import jsonify


test_pb = HarvestBlueprint(
    'test_bp', __name__
)


@test_pb.route('/test/aws')
def test_route():
    return jsonify('Successful Test Route')

