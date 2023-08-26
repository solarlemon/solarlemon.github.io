import datetime
import os
import re
import requests
from qiniu import Auth, put_file
import time


# 获取md文件中的图片链接,保存为文件，上传至七牛并返回七牛外链地址
def get_pic_url(blog_md_file):
    url_map = {}
    with open(blog_md_file, 'r', encoding='utf-8') as f:
        content = f.read()
        img_patten = r'!\[.*?\]\((.*?)\)|<img.*?src=[\'\"](.*?)[\'\"].*?>'
        matches = list(re.compile(img_patten).findall(content))  # 匹配图片
        if len(matches) > 0:  # 这里存放的matches是图片
            for url in matches:
                # url = url[0]
                url = url[1]
                # CSDN图片直链有3种样式，真坑:
                # 这一种文件名太长，直接这样命名上传到七牛云之后，有时外链链接无法加载.
                # https://imgconvert.csdnimg.cn/aHR0cDovL2ltZy5ibG9nLmNzZG4ubmV0LzIwMTcxMTE2MTQ1MjIxNTky,
                # 下面两种要去除后面的参数
                # https://img-blog.csdnimg.cn/20181206193427845.png?x-oss-process=image/watermark,type_ZmFuZ3poZW5naGVpdGk,shadow_10,text_aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3l3cTkzNQ==,size_16,color_FFFFFF,t_70
                # https://img-blog.csdn.net/20180626193940302?watermark/2/text/aHR0cHM6Ly9ibG9nLmNzZG4ubmV0L3l3cTkzNQ==/font/5a6L5L2T/fontsize/400/fill/I0JBQkFCMA==/dissolve/70
                print("图片原url:", url)
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML,'
                                      ' like Gecko) Chrome/55.0.2883.87 Safari/537.36'
                    }
                    if "csdn" in url:
                        # CSDN保存的图片
                        pic_name = url.split('csdnimg.cn/')[-1]
                        # pic_name = "{}/{}".format(pic_path, url.split('csdnimg.cn/')[-1])
                        pic_name = pic_name.split('csdn.net/')[-1]
                        pic_name = pic_name.split('?')[0]
                        # csdn部分直链链接里没有格式，加个图片尾缀
                        if not pic_name.endswith('.jpg') and not pic_name.endswith('.png'):
                            pic_name = pic_name + '.jpg'
                        response = requests.get(url, headers=headers).content
                        pic_name_len = len(pic_name)

                    elif "github" in url:
                        # github保存的图片，github直链的链接为文件链接加参数:?raw=true,例如:
                        # https://github.com/yinwenqin/kubeSourceCodeNote/blob/master/scheduler/image/p2/schedule.jpg?raw=true
                        pic_name = url.split('/')[-1]
                        url += "?raw=true"
                        response = requests.get(url, headers=headers).content
                        pic_name_len = len(pic_name)

                    elif "images" in url:
                        # 来自于本地文件
                        pic_name = url
                        new_pic_url = pic_upload(pic_name)
                        url_map[url] = new_pic_url
                        print("pic_name：", pic_name)
                        url_map[url] = new_pic_url

                except Exception as e:
                    print("文件:", blog_md_file, "url处理失败:", url, e)
                    return {}
    print(url_map)  # map：{原地址：上传后的地址}
    return url_map


# 获取所有的md文件
def list_file(files, path):
    # 取出指定路径下的所有文件，包含所有子目录里的文件
    items = os.listdir(path)
    for i in items:
        i_path = os.path.join(path, i)
        if os.path.isdir(i_path):
            list_file(i_path, files)
        else:
            if i_path.endswith(".md"):
                files.append(i_path)
    return files


# pic上传七牛云图床，获取图片在图床中的链接，替换md文档
def pic_upload(file):
    try:
        # 换成自己的认证及相关信息
        endpoint = "http://ryyg0t1v1.hn-bkt.clouddn.com"
        access_key = "pV-T3ApSlSJqKOeMnwlAX8HLa0KlCZhj2jP3VPPK"
        secret_key = "Y79350-7CMJgUytdmvOvlsucFC7HJQoQ4mV9m1NK"
        bucket_name = 'solarnote'
        key = os.path.basename(file)
        q = Auth(access_key, secret_key)
        token = q.upload_token(bucket_name, key, 3600)
        put_file(token, key, file)
        # 上传后得到的图片外链示例: http://pwh8f9az4.bkt.clouddn.com/images/AlgSchedule.jpg
        new_url = endpoint + '/' + os.path.basename(file)
        print('上传成功。new url：', new_url)
        return new_url

    except Exception as e:
        print('upload image to QiNiu oss failed:', file, e)
        return ""


# 替换md文件中的旧链接
def modify_md(blog_md_file, url_map):
    try:
        with open(blog_md_file, "r", encoding='utf-8') as f:
            content = f.read()
        for url, new_pic_url in url_map.items():
            # 根据匹配url_map进行修改
            with open(blog_md_file, "w", encoding='utf-8') as f:
                content = content.replace(url, new_pic_url)
                f.write(content)
                print(blog_md_file, "图片地址修改成功")
    except Exception as e:
        print(blog_md_file, '文件修改失败:', e)


def run(file):
    url_map = get_pic_url(file)
    if len(url_map.keys()) > 0:
        modify_md(file, url_map)


def main(path):
    # 获取所有的md文件
    files = SearchFiles(path, '.md')
    if len(files) > 0:

        for file in files:
            if compareFileTime(file) is False:  # 当前时间和修改时间不相同则不执行
                continue
            run(file)
    else:
        print("no markdown found, exit")


def SearchFiles(directory, fileType):
    fileList = []
    for root, subDirs, files in os.walk(directory):
        for fileName in files:
            if fileName.endswith(fileType):
                fileList.append(os.path.join(root, fileName))
    return fileList


def copy_to_hexo():
    TimeFormat = '%Y-%m-%d %H:%M:%S'
    blog_md_files = SearchFiles(LOCAL_ARTICLE_PATH, '.md')
    for file in blog_md_files:
        if compareFileTime(file) is False:  # 当前时间和修改时间不相同则不复制
            continue
        dirname, fileName = os.path.split(file)
        with open(file, 'r', encoding='utf-8') as f:
            # 读文件
            content = f.read()
            title = fileName.split('.')[0]
            content = "---\ntitle: " + title + "\ndate: " + datetime.datetime.now().strftime(
                TimeFormat) + "\ntags: xxx\ncategories: xxx\n---\n" + content
            # print(content)
        with open(md_path + '/' + fileName, "w", encoding="utf-8") as f:
            # 写文件
            try:
                f.write(content)
            except Exception as e:
                print(fileName, '失败', e)
        return title


# 文件修改时间与当前时间的比较,参数为文件名（路径）
def compareFileTime(filename):
    TimeFormat = '%Y-%m-%d %H'
    struct_time = time.strptime(time.ctime(os.path.getmtime(filename)), '%a %b %d %H:%M:%S %Y')
    fileTime = time.strftime(TimeFormat, struct_time)
    now = datetime.datetime.now().strftime(TimeFormat)
    # 同一分钟返回true
    return now == fileTime


if __name__ == "__main__":
    md_path = 'E:/blog/source/_posts/'  # 博客存放位置
    pic_path = 'E:/blog/source/images/'  # 这里是存放图片的目录
    LOCAL_ARTICLE_PATH = 'E:/VS Code刷leetcode/LeetCode-Train'  # 这里填入已写好的md文档
    fileName = copy_to_hexo()
    print(fileName, "成功复制到hexo博客目录下")
    # if fileName is not None:
    main(md_path)
