import unittest
from cloud_harvest_plugin_aws.tasks import get_nested_values


class TestGetNestedValues(unittest.TestCase):
    def setUp(self):

        # AI generated data
        self.simple_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "value"
                    },
                    "list": [
                        {"level4": "value1"},
                        {"level4": "value2"}
                    ]
                }
            },
            "top_level": "value"
        }

        # Simplified data structure from AWS EC2 describe_instances
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_instances.html
        self.practical_data = {
            "Reservations": [
                {
                    "Groups": [
                        {
                            "GroupId": "test-group-0"
                        },
                        {
                            "GroupId": "test-group-1"
                        },
                        {
                            "GroupId": "test-group-2"
                        }
                    ],
                    "Instances": [
                        {
                            "InstanceId": "test1-instance-0"
                        },
                        {
                            "InstanceId": "test1-instance-1"
                        },
                        {
                            "InstanceId": "test1-instance-2"
                        }
                    ]
                }
            ],
            "NextToken": "string"
        }

    def test_get_top_level_value(self):
        result = get_nested_values("top_level", self.simple_data)
        self.assertEqual(result, ["value"])

    def test_get_nested_value(self):
        result = get_nested_values("level1.level2.level3.level4", self.simple_data)
        self.assertEqual(result, ["value"])

    def test_get_value_from_list(self):
        result = get_nested_values("level1.level2.list.level4", self.simple_data)
        self.assertEqual(result, ["value1", "value2"])

    def test_get_non_existent_value(self):
        result = get_nested_values("non.existent.key", self.simple_data)
        self.assertEqual(result, [])

    def test_get_instances_from_practical_data(self):
        result = get_nested_values("Reservations.Instances", self.practical_data)
        expected_result = [
            {
                "InstanceId": "test1-instance-0"
            },
            {
                "InstanceId": "test1-instance-1"
            },
            {
                "InstanceId": "test1-instance-2"
            }
        ]
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()
