from cache.connection import HarvestCacheConnection
from bson import ObjectId
from datetime import datetime, timezone
from logging import getLogger

logger = getLogger('harvest')
_flat_record_separator = '.'


def set_pstar(client_writer: HarvestCacheConnection, **kwargs) -> ObjectId:
    """
    a PSTAR is a concept in Harvest where objects are stored on five dimensions
    ['harvest'][platform.service.type]
    :param client_writer: a HarvestCacheConnection writer configuration
    :param Platform: the cloud provider this database was retrieved from (ie AWS, Azure, Google)
    :param Service: the provider's service (ie "RDS", "EC2")
    :param Type: service's object classification (ie RDS "instance" or EC2 "event")
    :param Account: a unique identifier indicating the account or environment level for this service
    :param Region: the geographic region name for the objects retrieved from the underlying API call
    :param Count: number of records retrieved in the data collection job
    :param StartTime: when the data collection job was started
    :param EndTime: when the data collection job completed
    :param ApiVersion: version of this software
    :param Module: metadata of the collector used to collect the data
    :param Errors: provides and error messages
    :return:
    """

    client_writer.connect()

    # no need to replicate this logic everywhere
    kwargs['duration'] = duration_in_seconds(a=kwargs['EndTime'], b=kwargs['StartTime'])

    _id = None
    try:
        from datetime import datetime
        _id = client_writer['harvest']['pstar'].find_one_and_update(filter={k: kwargs.get(k) for k in ['Platform',
                                                                                                       'Service',
                                                                                                       'Type',
                                                                                                       'Account',
                                                                                                       'Region']},
                                                                    projection={'_id': 1},
                                                                    update={"$set": kwargs},
                                                                    upsert=True).get('_id')

    except Exception as ex:
        logger.error(f'{client_writer.log_prefix}: ' + ' '.join(ex.args))

    finally:
        return _id


def write_record(record: dict, meta_extra_fields: tuple = ()) -> tuple:
    """
    a record to be written to the harvest cache
    to qualify as a valid record, it must contain a key named Harvest with the following structure

    "Harvest": {
        "Platform": str,
        "Service": str,
        "Type": str,
        "Account": str,
        "Region": str,
        "Module": {
            "Name": str,
            "Version": str,
            "Repository": str
            "FilterCriteria": list
        },
        "Dates": {
            "LastSeen": datetime.datetime,
            "DeactivatedOn": datetime.datetime,
        },
        "Active": bool
    }
    :param record: a dictionary object representing a single record
    :param meta_extra_fields: extra fields to add to the meta collection
    :return: _id
    """
    from pymongo import ReplaceOne
    from flatten_json import flatten
    flat_record = flatten(record, separator=_flat_record_separator)

    replace_filter = {
        'Harvest': {
            'Module': {
                'UniqueFilter': record['Harvest']['Module']['UniqueFilter']
            }
        }
    }

    collection = get_collection_name(**record['Harvest'])

    replace_resource = ReplaceOne(filter=replace_filter,
                                  replacement=record,
                                  upsert=True)

    replace_meta = ReplaceOne(filter=replace_filter,
                              replacement={
                                  "Collection": "",
                                  "UniqueIdentifier": record['Harvest']['Module']['UniqueFilter'],
                                  "Harvest": record["Harvest"],
                                  **{k: record.get(k) or flat_record.get(k) for k in meta_extra_fields}
                              },
                              upsert=True)

    result = (collection, replace_resource, replace_meta)
    return result


def write_records(client: HarvestCacheConnection, records: list) -> list:
    """
    top-level co
    :param client: a HarvestCacheConnection writer configuration
    :param records:
    :return:
    """

    bulk_records = {'meta': []}
    for record in records:
        collection, record_replace, meta_replace = write_record(record=record)

        if not bulk_records.get(collection):
            bulk_records[collection] = []

        bulk_records[collection].append(record_replace)
        bulk_records['meta'].append(meta_replace)

    # perform bulk writes by collection but always do 'meta' last
    updated_records = [client['harvest'][collection].bulk_write(bulk_records[collection])
                       for collection in list([k for k in bulk_records.keys()
                                               if k not in 'meta'] + ['meta'])]
    return updated_records


def duration_in_seconds(a: datetime, b: datetime) -> int or float:
    """
    a simple, testable function for retrieving the number of seconds between two dates
    :param a: a datetime
    :param b: another datetime
    :return: an integer or float representing the number of seconds between two datetime objects
    """

    return abs((a - b).total_seconds())


def get_collection_name(**harvest_metadata) -> str:
    """
    returns the collection name used in a pstar record write based on the Harvest metadata key
    :param harvest_metadata: the "Harvest": {} key generated by a pstar record write
    :return: str
    """
    return '.'.join((harvest_metadata['Platform'],
                     harvest_metadata['Service'],
                     harvest_metadata['Type']))


def get_unique_filter(record: dict, flat_record: dict) -> dict:
    """
    retrieves the unique identifier defined by the module for this record
    :param record: original record
    :param flat_record: flattened record
    :return: a new dict of field: fieldValue
    """
    return {field: flat_record.get(field) for field in record['Harvest']['Module']['FilterCriteria']}


def deactivate_records(client_writer: HarvestCacheConnection, collection_name: str, record_ids: list) -> dict:
    collection = client_writer['harvest'][collection_name]

    # deactivate records which were not inserted/updated in this write operation
    records_to_deactivate = [r["_id"] for r in collection.find({"Harvest.Active": True, "_id": {"$nin": record_ids}},
                                                               {"_id": 1})]

    update_set = {"$set": {"Harvest.Active": False,
                           "Harvest.Dates.DeactivatedOn": datetime.now(tz=timezone.utc)}}

    update_many = collection.update_many(filter={"_id": {"$in": records_to_deactivate}},
                                         update=update_set)

    # update the meta cache
    collection = client_writer['harvest']['meta']
    update_meta = collection.update_many(filter={"Collection": collection_name,
                                                 "CollectionId": {"$in": records_to_deactivate}},
                                         update=update_set)

    logger.debug(f'{client_writer.log_prefix}: harvest.{collection_name}: deactivated {update_many.modified_count}')

    return {
        'deactivated_ids': records_to_deactivate,
        'modified_count': update_many.modified_count,
        'meta_count': update_meta.modified_count
    }


def add_indexes(client_writer: HarvestCacheConnection, indexes: dict):
    """
    create an index in the backend cache
    :param client_writer: a HarvestCacheConnection writer configuration
    :param indexes: a dictionary of the {database: {collection: [fielda, fieldb]}} construct
    :return:
    """
    # verify connection
    client_writer.connect()

    # identify databases
    for database in indexes.keys():
        # identify collections
        for collection in indexes['harvest'].keys():
            # identify indexes
            for index in indexes['harvest'][collection]:
                if isinstance(index, (str or list)):
                    client_writer['harvest'][collection].create_index(keys=index)
                    logger.debug(f'{client_writer.log_prefix}: added index: {database}.{collection}.{str(index)}')

                elif isinstance(index, dict):
                    # pymongo is very picky and demands a list[tuple())
                    keys = [(i['field'], i.get('sort', 1)) for i in index.get('keys', [])]

                    client_writer['harvest'][collection].create_index(keys=keys, **index['options'])

                    logger.debug(f'{client_writer.log_prefix}: added index: {database}.{collection}.{str(index)}')

                else:
                    logger.error(f'unexpected type for index `{index}`: {str(type(index))}')


def check_harvest_metadata(flat_record: dict) -> bool:
    if not flat_record:
        return False

    required_fields = ('Platform',
                       'Service',
                       'Type',
                       'Account',
                       'Region',
                       'Module.FilterCriteria.0',       # FilterCriteria requires at least one value, so .0 is expected
                       'Module.Name',
                       'Module.Repository',
                       'Module.Version',
                       'Dates.DeactivatedOn',
                       'Dates.LastSeen',
                       'Active')

    for field in required_fields:
        field_name = _flat_record_separator.join(['Harvest', field])

        if field_name not in flat_record.keys():
            logger.warning('record failed harvest metadata check: ' + field_name)
            return False

    return True
