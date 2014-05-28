import zmq
import pymongo
import bson

# TODO NO SECURITY IS IMPLEMENTED !!!!

client = pymongo.MongoClient()
db = client.snakeflow
running = db.running
workflows = db.workflows

context = zmq.Context(1)
server = context.socket(zmq.REP)
server.bind("tcp://127.0.0.1:6001")

while True:
    request = server.recv_json()
    print("Got request: " + str(request))
    print()
    try:
        if request['user'] not in ['adr']:  # TODO use new security framework
            server.send_json({'error': 'invalid user'})
            continue

        if request['type'] == 'register':
            if 'data' not in request:
                server.send_json({'error': 'submit needs data'})
            if 'updates' not in request['data']:
                request['data']['updates'] = []
            jobid = running.insert(request['data'])
            server.send_json({'jobid': str(jobid)})

        if request['type'] == 'update':
            assert 'jobid' in request
            assert 'data' in request
            res = running.update(
                {'_id': bson.ObjectId(request['jobid'])},
                {'$push': {'updates': request['data']}}
            )
            assert res['nModified'] == 1
            server.send_json({'status': 'ok'})

        if request['type'] == 'finished':
            assert 'jobid' in request
            res = running.update(
                {'_id': bson.ObjectId(request['jobid'])},
                {'$set': {'finished': True}}
            )
            assert res['nModified'] == 1
            server.send_json({'status': 'ok'})

    except Exception as e:
        print(e)
        server.send_json({'error': 'internal'})
