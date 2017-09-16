def parseException(data):
    traceback = []

    for value in data['values']:
        for frame in value['stacktrace']['frames']:
            context = 'File {filename}, line {lineno}, in {function}\n'.format(**frame)

            try:
                context += '  {}'.format(frame['context_line'].strip())
            except KeyError:
                context += '  {}'.format(frame['vars']['value'])

            traceback.append(context)

    return '\n'.join(traceback)


def parseMessage(data):
    return str(data['message'])
