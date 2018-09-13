"""
下载B站指定视频
"""


from contextlib import closing
import requests
import sys,os
import re
import json
import shutil
import re
from bs4 import BeautifulSoup
import threading
import getopt
from pprint import pprint
import sys
# 下载地址的镜像格式部分的可能替换值
video_mode = [ 'mirrorcos.', 'mirrorkodo.', 'mirrorks3.', 'mirrorbos.', 'mirrorks3u.',  ]

# 主线程
main_thread = threading.current_thread()

def make_path(p):  
    """
        判断文件夹是否存在
        存在则清空
        不存在则创建
    """
    #if os.path.exists(p):       # 判断文件夹是否存在  
    #    shutil.rmtree(p)        # 删除文件夹  
    if not os.path.exists(p):
        os.mkdir(p)                 # 创建文件夹  


        
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.bilibili.com'}

sess = requests.Session()

#下载的根目录
root_dir = '.'          

def download_video(video_url, dir_, video_name, index):
    size = 0
    '''
        当使用requests的get下载大文件/数据时，建议使用使用stream模式。
        当把get函数的stream参数设置成False时，它会立即开始下载文件并放到内存中，如果文件过大，有可能导致内存不足。
        当把get函数的stream参数设置成True时，它不会立即开始下载，当你使用iter_content或iter_lines遍历内容或访问内容属性时才开始下载。需要注意一点：文件没有下载之前，它也需要保持连接。
        iter_content：一块一块的遍历要下载的内容
        iter_lines：一行一行的遍历要下载的内容
    '''
    session = requests.Session() 
    
    mirror = re.findall('mirror.*?\.', video_url)
    # 链接中是否带mirror字符
    isMirror = len(mirror) > 0   
    chunk_size = 102400 * 4 #每次400KB
    video_name = os.path.join(dir_, video_name, str(index) + '.flv')
    
    for i,mode in enumerate(video_mode):  
        video_url = re.sub('mirror.*?\.', mode, video_url)
        try:
            response = session.get(video_url, headers=headers, stream=True, verify=False)
        except Exception as e:
            print("下载视频 %s 失败" % video_url)
            continue
            
        if response.status_code == 200:
            content_size = int(response.headers['content-length'])
            sys.stdout.write('第%d个片段：[文件大小]:%0.2f MB\n' % (index, content_size / 1024 / 1024))
            with open(video_name, 'wb') as file:
                for data in response.iter_content(chunk_size = chunk_size):
                    file.write(data)
                    size += len(data)
                    file.flush()

                    sys.stdout.write('第%d个片段：[下载进度]:%.2f%%' % (index, float(size / content_size * 100)) + '\r')
                    sys.stdout.flush()
                    if size / content_size == 1:
                        print('\n')   
            return
        
        else:
           
            print('此链接异常，尝试更换链接')
            
            if not isMirror or i == len(video_mode) - 1:
                print('此视频片段无法下载') 
                return
            
            


def download_videos(dir_, video_urls, video_name):
    make_path(os.path.join(dir_, video_name))
    print('正在下载 %s 到 %s 文件夹下' %(video_name, os.path.join(dir_, video_name)))
    
    print("共有%d个片段需要下载" %len(video_urls))
    for i, video_url in enumerate(video_urls):      
        
        t = threading.Thread(target=download_video, kwargs={'video_url': video_url, 'dir_': dir_, 'video_name': video_name, 'index': i+1})
        t.setDaemon(True)
        t.start()
        
        #download_video(video_url, dir_, video_name, i+1)
    
    for t in threading.enumerate():
        if t is threading.current_thread():
            continue
        t.join()
    
    print(' %s 下载完成' %video_name)
                
def get_download_urls(arcurl):
    req = sess.get(url=arcurl, verify=False,headers=headers)
    pattern = r'<script>window.__playinfo__=(.*?)</script>?'
    try:
        infos = re.findall(pattern, req.text)[0]
    except:
        return []
    # print(infos)
    json_ = json.loads(infos)
    durl = json_['durl']
    
    #urls = [re.sub('mirror.*?\.', 'mirrorcos.', url['url']) for url in durl]
    urls = [url['url'] for url in durl]
    
    return urls

def get_page_count(aid):
    """
        获取一个视频的页数
    """
    url = 'https://api.bilibili.com/x/web-interface/view?aid=%s' % aid
    req = sess.get(url,headers=headers,verify=False)
    pattern = '\"pages\":(\[.*\]),\"embedPlayer\"'
    try:
        data = json.loads(req.text)["data"]
    except: 
        print("获取视频 %s 页码失败" % aid)
        return
    title_pages = dict([(page['part'],page['page']) for page in data["pages"]])
    title = data['title']
    return title_pages, title

def download_all(aid, start_page = 1):
    """
        给定一个视频号，下载所有的视频
    """
    url = 'https://www.bilibili.com/video/av%s'%aid
    try:
        title_pages, title = get_page_count(aid)
    except Exception as e:
        print(e)
        print("获取视频 %s 页码失败" % aid)
        return

    title = title.strip("/,\\,.,_哔哩哔哩 (゜-゜)つロ 干杯~-bilibili, ")
    title = title.replace('/','').replace('\\','')
    dir_ = os.path.join(root_dir, title)
    
    make_path(dir_)
    print('创建文件夹 %s 成功' %dir_)
    for title,page in title_pages.items():
        if page < start_page:
            continue
        video_url = url + '/?p=%d' %page
        try:
            urls = get_download_urls(video_url)
        except Exception as e:
            print("获取视频 %s url地址失败" % video_url)
            continue
        download_videos(dir_, urls, '%s.flv' %title)


def download_by_user (mid):
    page = 1
    size = 25
    total = 25
    base_url = 'https://space.bilibili.com/ajax/member/getSubmitVideos?mid=%d&page=%d&pagesize=%d'
    vids = []
    while page*size <= total:
        url = base_url % (mid,page,size)
        try:
            req = sess.get(url,headers=headers)
        except Exception as e:
            print("获取用户 %d 第 %d 页视频失败" %(mid,page))
            page +=1
            continue
        if (req.status_code != 200):
            print(url + ' not found')
            return
        data = json.loads(req.text)
        total = data["data"]["count"]
        vlist = data["data"]["vlist"]
        for v in vlist:
            vids.append(v["aid"])
        page += 1
    ts = []
    for v in vids:
        t = threading.Thread(target=download_all,kwargs={"aid":v})
        ts.append(t)
        t.start()
    for t in ts:
        if t is main_thread:
            continue
        t.join()


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hu:a:", ["help", "user=","av="])
    except Exception as e:
        print("参数错误")
        exit()
    for opt in opts:
        if opt[0] == '-u' or opt[0] == '--user':
            download_by_user(int(opt[1]))
        if opt[0] == '-h' or opt[0] == '--help':
            print("no help")
        if opt[0] == '-a' or opt[0] == '--av':
            download_all(opt[1],1)