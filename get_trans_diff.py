# coding=utf-8
import os
import json
import urllib2
import commands
import sys
import re

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


# 执行和打印git指令
def run_git_command(command):
    (status, output) = commands.getstatusoutput(command)
    if status == 0:
        print '(success) ' + command
    else:
        print '(failed)  ' + command
        print output
        sys.exit()


# 找到项目中支持的语言
def find_lang_support():
    languages = []
    for root, dirs, files in os.walk("app/src/main/res"):
        for dirItem in dirs:
            # 文件夹名称要包含value-，不能包含数字、dpi、night
            if 'values-' in dirItem and not (bool(re.search(r'\d', dirItem))) \
                    and 'dpi' not in dirItem and 'night' not in dirItem:
                languages.append(dirItem.split('-', 1)[1])
    # print languages
    return languages


# 找到values文件夹下的strings文件
def find_strings_xml():
    strings = []
    for root, dirs, files in os.walk("app/src/main/res/values"):
        for fileItem in files:
            if 'strings' in fileItem:
                strings.append(fileItem)
    # print strings
    return strings


# 读取并解析xml文件
def parse_xml(languages, strings):
    result = {
        'diff': {},
        'string_items': {}
    }

    for language in languages:
        result['diff'][language] = []
        result['string_items'][language] = []

    for string in strings:
        # 默认语言路径
        defaultPath = 'app/src/main/res/values/' + string
        originXml = {}

        for language in languages:
            # 默认语言块
            originXml[language] = parse_strings_xml(defaultPath)

            path = 'app/src/main/res/values-' + language + '/' + string
            langXml = parse_strings_xml(path)

            langTrans = {}
            for key, value in originXml[language].items():
                langTrans[key] = value

            # 找到每个语言和默认语言key的区别
            for key in originXml[language].keys():
                if key in langXml.keys():
                    if langTrans[key]['tag'] == 'string':
                        langTrans[key]['value_items'][0]['translate'] = langXml[key]['value_items'][0]['text']
                    else:
                        for i in range(len(langTrans[key]['value_items']) - 1):
                            langTrans[key]['value_items'][i]['translate'] = langXml[key]['value_items'][i]['text']
                else:
                    if originXml[language][key]['translatable']:
                        result['diff'][language].append(key)
                    else:
                        langTrans.pop(key)

            for key in langTrans.keys():
                result['string_items'][language].append(langTrans[key])

    # print(json.dumps(result, sort_keys=True, separators=(', ', ': ')))
    return result


# 解析某个语言路径下的xml文件
def parse_strings_xml(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except IOError:
        return {}

    langXml = {}

    for child in root:
        if child.tag == 'string-array' or child.tag == 'plurals':
            valueItems = []
            for grandson in child:
                valueItems.append({
                    'attribs': grandson.attrib,
                    'text': grandson.text,
                    'translate': ''
                })
            # 这里string-array和plurals不支持translatable属性, 强制都必须有翻译
            langXml[child.attrib['name']] = {
                'key': child.attrib['name'],
                'tag': child.tag,
                'translatable': True,
                'value_items': valueItems
            }
        elif child.tag == 'string':
            if 'translatable' in child.attrib:
                translatable = False if child.attrib['translatable'] == 'false' else True
            else:
                translatable = True
            langXml[child.attrib['name']] = {
                'key': child.attrib['name'],
                'tag': 'string',
                'translatable': translatable,
                'value_items': [{
                    'text': child.text,
                    'translate': ''
                }]
            }
    return langXml


def main():
    request = urllib2.Request("https://api.github.com/repos/ParticleMedia/Android/pulls")
    request.add_header('Authorization', 'token 4dc4f585e3ddf3d09208c2f870832ab771f2fd4a')
    response = urllib2.urlopen(request)
    data = json.loads(response.read())

    prInfo = []
    prNumbersFile = open('currentPrNumbers.txt', 'r+')
    for line in prNumbersFile.readlines():
        prInfo.append(line.strip())
    prNumbersFile.close()

    transJson = {}
    prNeedRecord = []
    hasNotRecordFirst = True
    prCheck = None
    for item in data:
        prItem = str(item['number']) + ',' + item['head']['sha']
        if prItem not in prInfo:
            if hasNotRecordFirst:
                prCheck = item['head']['ref']
                # os.chdir("./DemoAIT")
                transJson['pr_label'] = item['number']
                transJson['pr_link'] = item['html_url']
                transJson['jira_label'] = 'CA-1550' # todo test data
                transJson['jira_link'] = 'https://particlemedia.atlassian.net/browse/' + transJson['jira_label']
                # transJson['branch_from'] = item['base']['ref']
                transJson['branch_from'] = 'feature/addDog'
                # transJson['branch_to'] = item['head']['ref']
                transJson['branch_to'] = 'master'
                # run_git_command('git pull')
                # run_git_command('git checkout ' + item['head']['sha'])
                parseXml = parse_xml(find_lang_support(), find_strings_xml())
                prNeedRecord.append(prItem)
                transJson['diff'] = parseXml['diff']
                transJson['string_items'] = parseXml['string_items']
                print(json.dumps(transJson, sort_keys=True, separators=(', ', ': ')))
                hasNotRecordFirst = False
        else:
            prNeedRecord.append(prItem)

    prNumbersFile2 = open('currentPrNumbers.txt', 'w+')
    for needRecord in prNeedRecord:
        prNumbersFile2.write(str(needRecord) + '\n')
    prNumbersFile2.close()
    # print prCheck


if __name__ == '__main__':
    main()
