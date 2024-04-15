from flask import Blueprint, jsonify

test_pb = Blueprint(
    'test_bp', __name__
)


@test_pb.route('/test/aws')
def test_route():
    return jsonify('Successful Test Route')

