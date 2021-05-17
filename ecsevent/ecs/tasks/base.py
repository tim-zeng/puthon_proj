def auto_add_modify_delete_items(tableObj, onlineDataList, keys=[], filters=[]):
    '''
        根据线上数据，自动添加、修改、删除表里的数据。
        keys为组合key，filters为过滤条件
    '''
    exist_items = tableObj.query.filter(*filters).all()
    storedDict = {}
    for item in exist_items:
        keyname = item.id
        if type(keys) == list and len(keys) > 0:
            keyname = '_'.join([str(getattr(item, k)) for k in keys])
        storedDict[keyname] = item

    # 添加数据库中不存在的， 修改变更的
    add_list = []
    exist_number = 0
    full_keys = []
    for _item in onlineDataList:
        keyname = _item.get('id')
        if type(keys) == list and len(keys) > 0:
            keyname = '_'.join([str(_item[k]) for k in keys])
        full_keys.append(keyname)
        item = storedDict.get(keyname)
        if item:
            if item.to_dict().items() != _item.items():
                for attr, value in _item.items():
                    setattr(item, attr, value)
                item.save()
            exist_number += 1
            continue
        if _item not in add_list:
            add_list.append(_item)
    for _item in add_list:
        tableObj(**_item).save()

    # 删除数据库中多余的
    delete_number = 0
    for _id in set(storedDict.keys()).difference(set(full_keys)):
        item = storedDict.get(_id)
        if item:
            item.delete()
            delete_number += 1
    add_number = len(add_list)
    msg = f'{tableObj.__tablename__} add number :{add_number}, delete_number:{delete_number}, exist_number:{exist_number}, sql_rows:{len(exist_items)}'
    print(msg)
    return msg

