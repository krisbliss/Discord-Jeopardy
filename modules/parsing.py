import re
import urllib.parse as urlparse
import xml.etree.ElementTree as ET

def parse_youtube_video(url):
    """Extracts the 11-char ID and converts timestamps (e.g. t=1m4s) to seconds."""
    if not url: return None, 0
    
    # Extract ID
    regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    video_id = match.group(1) if match else None
    
    if not video_id: return None, 0

    # Extract Timestamp
    parsed = urlparse.urlparse(url)
    qs = urlparse.parse_qs(parsed.query)
    t_str = qs.get('t', qs.get('start', ['']))[0]
    
    start_seconds = 0
    if t_str:
        if t_str.isdigit():
            start_seconds = int(t_str)
        else:
            time_regex = r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
            t_match = re.match(time_regex, t_str)
            if t_match:
                h = int(t_match.group(1) or 0)
                m = int(t_match.group(2) or 0)
                s = int(t_match.group(3) or 0)
                start_seconds = (h * 3600) + (m * 60) + s

    return video_id, start_seconds

def parse_jeopardy_xml(xml_string):
    # Cleans and parses the XML string into a dictionary.
    try:
        clean_xml = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', xml_string)
        
        root = ET.fromstring(clean_xml)
        categories = []
        for cat in root.findall('category'):
            cat_data = {'name': cat.get('name'), 'questions': []}
            for entry in cat.findall('entry'):
                video_node = entry.find('video')
                video_url = video_node.text if video_node is not None else None
                
                # return tuple of video id and starting position
                vid_id, vid_start = parse_youtube_video(video_url)
                
                # find the source tag
                source_node = entry.find('source')
                
                cat_data['questions'].append({
                    'value': entry.get('value'),
                    'question': entry.find('question').text,
                    'answer': entry.find('answer').text,
                    'source': source_node.text if source_node is not None else 'Trust me bro',
                    'video_id': vid_id,
                    'video_start': vid_start,
                    'used': False
                })
            categories.append(cat_data)
        return categories
    except Exception as e:
        print(f"XML Error: {e}")
        return None
