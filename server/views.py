from base64 import b64decode, b64encode

from django.db.transaction import atomic

from pool.local import LocalPool
from utils.api import Api

from .models import Node, User

pool = LocalPool('var')
api = Api()


@api.api
def check_hash(l):
    return list(filter(pool.__contains__, l))


@api.api
def put_block(l):
    for block in l:
        hash = block['hash']
        data = b64decode(block['data'])
        pool[hash] = data


@api.api
def update_tree(add, remove):
    with atomic():
        user = User.get()
        for item in remove:
            path = b64decode(item['path'])
            node = user.find(path)
            if node.name == b'/':
                node.meta = b''
                node.save()
            else:
                node.delete()
        for item in add:
            path = b64decode(item['path'])
            is_dir = item['is_dir']
            dir, _, part = path.rstrip(b'/').rpartition(b'/')
            meta = b64decode(item['meta'])
            size = 0
            for hash in item['blocks']:
                size += pool.get_size(hash)
            blocks = '\n'.join(item['blocks'])
            node = user.find(dir, create=True)
            try:
                node = node.children.get(name=part)
                node.meta = meta
                node.save()
            except Node.DoesNotExist:
                node.children.create(name=part, is_dir=is_dir, meta=meta, size=size, blocks=blocks)


@api.api
def get_tree(base):
    with atomic():
        user = User.get()
        base = user.find(b64decode(base))
        return base.list(prefix=b'')


@api.api
def get_block(l):
    return {h: b64encode(pool[h]).decode('ascii') for h in l}


@api.api
def reset():
    from os import listdir, remove
    for f in listdir('var'):
        if len(f) == 64:
            remove('var/' + f)
    User.get().delete()
