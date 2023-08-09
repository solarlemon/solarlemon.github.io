import re
import requests
import os
from qiniu import Auth, put_file
from concurrent.futures import ThreadPoolExecutor


# 获取md文件中的图片链接,保存为文件，上传至七牛并返回七牛外链地址
def get_pic_url(filename):
    url_map = {}
    with open(filename, 'r',) as f:
        content = f.read()
        img_patten = r'!\[.*?\]\((.*?)\)|<img.*?src=[\'\"](.*?)[\'\"].*?>'
        matches = list(re.compile(img_patten).findall(content))
        if len(matches) > 0:
            for url in matches:
                url = url[0]
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
                        pic_name = url.split('csdnimg.cn/')[-1]
                        # pic_name = "{}/{}".format(pic_path, url.split('csdnimg.cn/')[-1])
                        pic_name = pic_name.split('csdn.net/')[-1]
                        pic_name = pic_name.split('?')[0]
                        # csdn部分直链链接里没有格式，加个图片尾缀
                        if not pic_name.endswith('.jpg') and not pic_name.endswith('.png'):
                            pic_name = pic_name + '.jpg'

                    elif "github" in url:
                        # 保存github图片，github直链的链接为文件链接加参数:?raw=true,例如:
                        # https://github.com/yinwenqin/kubeSourceCodeNote/blob/master/scheduler/image/p2/schedule.jpg?raw=true
                        pic_name = url.split('/')[-1]
                        url += "?raw=true"

                    else:
                        # 别的来源的图片链接如有不同，请自行按对应格式修改
                        pic_name = url.split('/')[-1]

                    response = requests.get(url, headers=headers).content

                    pic_name_len = len(pic_name)
                    # 名字太长截取一半
                    if pic_name_len > 40:
                        pic_name = pic_name[int(pic_name_len/2):]
                    pic_name = "{}/{}".format(pic_path, pic_name)
                    print(pic_name)
                    with open(pic_name, 'wb') as f2:
                        f2.write(response)
                    new_pic_url = pic_upload(pic_name)
                    url_map[url] = new_pic_url

                except Exception as e:
                    print("文件:", filename, "url处理失败:", url, e)
                    return {}
    print(url_map)
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
        # 上传后得到的图片外链示例: http://pwh8f9az4.bkt.clouddn.com/AlgSchedule.jpg
        new_url = endpoint + '/' + os.path.basename(file)
        # print('new url', new_url)
        return new_url

    except Exception as e:
        print('upload image to QiNiu oss failed:', file, e)
        return ""


# 替换md文件中的旧链接
def modify_md(filename, url_map):
    try:
        with open(filename, "r") as f:
            content = f.read()
        for url, new_pic_url in url_map.items():
            with open(filename, "w") as f:
                content = content.replace(url, new_pic_url)
                f.write(content)
    except Exception as e:
        print(filename, '文件修改失败:', e)


def run(file):
    # {old_url: new_url}
    url_map = get_pic_url(file)
    if len(url_map.keys()) > 0:
        modify_md(file, url_map)


def main(path):
    # 获取所有的md文件
    files = list_file([], path)
    if len(files) > 0:
        th_pool = ThreadPoolExecutor(20)
        for file in files:
            th_pool.submit(run, file)
        th_pool.shutdown(wait=True)
    else:
        print("no markdown found, exit")


if __name__ == "__main__":
    md_path = "E:/blog/source/_posts"
    pic_path = "E:/blog/source/images"
    if not os.path.exists(pic_path):
        os.makedirs(pic_path)
    main(md_path)

