import json, re, sys
import pyarrow.parquet as pq
OR=json.load(open('or/m_output_modalities=all.json')); OR=OR.get('data',OR)
def norm(s):
    s=s.lower()
    s=re.sub(r'\(.*?\)','',s)
    s=s.split(':',1)[1] if ':' in s else s
    s=re.sub(r'[-_/]',' ',s)
    s=re.sub(r'\b(preview|latest|thinking|instruct|it)\b',' ',s)
    s=re.sub(r'\b\d{4,8}\b',' ',s)
    return ' '.join(s.split())
idx={}
for m in OR:
    for k in (norm(m['name']), norm(m['id'].split('/',1)[1])):
        idx.setdefault(k,m)
ALIAS={
 'dreamina seedance 2.0':'bytedance/seedance-2.0','dreamina seedance 2.5':'bytedance/seedance-2.5',
 'minimax h3':'minimax/hailuo-3','happyhorse 1.0':'alibaba/happyhorse-1.0','veo 3.1':'google/veo-3.1',
 'veo 3.1 fast':'google/veo-3.1-fast','grok imagine video':'x-ai/grok-imagine-video','wan 2.7':'alibaba/wan-2.7',
 'wan 2.6':'alibaba/wan-2.6','runway gen 4.5':'runway/gen-4.5','kling 3.0 pro':'kwaivgi/kling-v3.0-pro',
 'hailuo 2.3':'minimax/hailuo-2.3','kling o1 pro':'kwaivgi/kling-video-o1','flux 3 video':'black-forest-labs/flux-3-video',
 'gemini 3.1 flash image':'google/gemini-3.1-flash-image','qwen image 3.0 pro':'qwen/qwen-image-3-pro',
 'mai image 2.5':'microsoft/mai-image-2.5','gemini 3.1 flash lite image':'google/gemini-3.1-flash-lite-image',
 'seedream 5.0 pro':'bytedance-seed/seedream-5-0-pro','gemini 3 pro image':'google/gemini-3-pro-image',
 'qwen image 2.1':'qwen/qwen-image-2.1-pro','minimax h3 image':'minimax/minimax-h3-image',
 'flux.2 [max]':'black-forest-labs/flux.2-max','flux.2 [flex]':'black-forest-labs/flux.2-flex','flux.2 [pro]':'black-forest-labs/flux.2-pro',
 'seedream 4.5':'bytedance-seed/seedream-4.5','seedream 5.0 lite':'bytedance-seed/seedream-5-0-lite',
 'recraft v4.1 utility pro':'recraft/recraft-v4.1-utility-pro','recraft v4.1 pro':'recraft/recraft-v4.1-pro',
 'gemini 2.5 flash image':'google/gemini-2.5-flash-image','gpt image 2':'openai/gpt-image-2',
}
BYID={m['id']:m for m in OR}
def find(name):
    k=norm(name)
    if k in ALIAS: return BYID.get(ALIAS[k])
    return idx.get(k)
KINDS={
 'chat':('text',['overall'],'text',None),
 'write':('text',['creative_writing'],'text',None),
 'summarise':('text',['longer_query','overall'],'text',None),
 'reason':('text',['math','hard_prompts'],'text',None),
 'code':('text',['coding','industry_software_and_it_services'],'text',None),
 'tools (proxy)':('text',['instruction_following','multi_turn'],'text','tools'),
 'extract (proxy)':('text',['instruction_following'],'text','structured_outputs'),
 'read.long':('text',['longer_query'],'text',None),
 'facts + check (proxy)':('text',['expert','hard_prompts'],'text',None),
 'research (proxy)':('text',['expert','hard_prompts'],'text','tools'),
 'write.lang / translate':('text',['non_english'],'text',None),
 'read.image':('vision',['overall','ocr'],'text','IMG_IN'),
 'read.pdf':('document',['overall'],'text','DOC_IN'),
 'image.make':('text_to_image',['overall'],'image',None),
 'image.edit':('image_edit',['overall'],'image','IMG_IN'),
 'video.make':(('text_to_video','image_to_video'),['overall'],'video',None),
}
LV=['ULTRA','MAX','HIGH','MID','LOW']
def split(lst):
    n=len(lst); base=n//5; extra=n%5
    sizes=[base]*5
    for i in [3,2,4,1,0][:extra]: sizes[i]+=1
    out={}; p=0
    for lv,s in zip(LV,sizes): out[lv]=lst[p:p+s]; p+=s
    return out
res={}; unmatched={}
for kind,(board,cats,out,need) in KINDS.items():
    boards=board if isinstance(board,tuple) else (board,)
    score={}; seen_names={}
    for b in boards:
        t=pq.read_table(f'lma/{b}.parquet').to_pandas()
        for c in cats:
            r=t[(t.category==c)&(t.vote_count>=200)]
            for _,row in r.iterrows():
                m=find(row.model_name)
                if not m:
                    unmatched.setdefault(kind,set()).add(row.model_name); continue
                a=m['architecture']; sp=m.get('supported_parameters') or []
                if out not in a['output_modalities']: continue
                if need=='tools' and 'tools' not in sp: continue
                if need=='structured_outputs' and not ({'structured_outputs','response_format'}&set(sp)): continue
                if need=='IMG_IN' and 'image' not in a['input_modalities']: continue
                if need=='DOC_IN' and not ({'file','image'}&set(a['input_modalities'])): continue
                k=(m['id'],b,c)
                if k in score and score[k][0]>=row.rating: continue
                score[k]=(row.rating,row.model_name)
    agg={}
    for (mid,b,c),(r,nm) in score.items():
        agg.setdefault(mid,[]).append((r,nm))
    import time
    cut=time.mktime((2025,5,16,0,0,0,0,0,0))
    allr=sorted(((sum(x[0] for x in v)/len(v),mid,v[0][1]) for mid,v in agg.items() if (BYID[mid].get('created') or 0)>=cut),reverse=True)
    top=allr[0][0] if allr else 0
    BANDS=[('ULTRA',0,25),('MAX',25,50),('HIGH',50,80),('MID',80,120),('LOW',120,190)]
    levels={}
    for lv,a,b in BANDS:
        g=[x for x in allr if top-b < x[0] <= top-a][:4]
        levels[lv]=[{'id':mid,'name':nm,'score':round(sc,1)} for sc,mid,nm in g]
    method='quality bands (Elo below the best: 0-25 / 25-50 / 50-80 / 80-120 / 120-190)'
    if min(len(v) for v in levels.values())<2:
        method='rank split of the best 20 (board too small for bands)'
        levels={lv:[{'id':mid,'name':nm,'score':round(sc,1)} for sc,mid,nm in g] for lv,g in split(allr[:20]).items()}
    n=sum(len(v) for v in levels.values())
    res[kind]={'n':n,'top':round(top,1),'method':method,'levels':levels}
json.dump(res,open('pipe2/tables.json','w'),indent=1)
for k,v in res.items(): print(f"{k:28s} {v['n']}")
print('\nTOP UNMATCHED (first 12 per kind):')
for k,v in unmatched.items(): print(k, sorted(v)[:12])
