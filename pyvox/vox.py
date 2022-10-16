from struct import unpack_from
import logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

import numpy as np

from .config import *
from .exceptions import AssigningException, ParsingException
from .models import *

class Chunk():
    
    def __init__(self,id,content=None,children=None):
        self.id = id
        self.name = str(id)[2:-1]
        self.content = content or b''
        self.children = children or []
        self.offset=0
        self._parse()
    
    def _parse(self):

        if self.id == b'MAIN':
            if len(self.content):
                raise ParsingException('Empty main chunk')
        
        elif self.id == b'PACK':
            logging.debug('Detect Pack chunk which is not supportted in current version, skip now')
        
        elif self.id == b'SIZE':
            self.size=unpack_from(SIZE_FMT,self.content,0)

        elif self.id == b'XYZI':
            n = int(unpack_from(XYZI_FMT_1,self.content,0)[0])
            self.voxels = []
            for i in range(n):
                self.voxels.append(unpack_from(XYZI_FMT_2, self.content, 4+4*i))

        elif self.id == b'RGBA':
            self.palette=[]
            for i in range(255):
                self.palette.append(unpack_from(RGBA_FMT, self.content, 4*i))

        elif self.id == b'MATL':
            _id = unpack_from('i', self.content)
            _dict = Bdict(self.content,4).dic
            self.material=Material(_id,_dict)

        elif self.id == b'nTRN':
            _id = unpack_from('i', self.content)
            frames = []
            bdict = Bdict(self.content,4)
            (c_id,r_id,l_id,frames_num)=unpack_from('iiii', self.content,bdict.offset)
            offset=16+bdict.offset
            for i in range(frames_num):
                _bdict=Bdict(self.content,offset)
                frames.append(_bdict.dic)
                offset=_bdict.offset
            self.ntrn=nTRN(_id,bdict.dic,c_id,r_id,l_id,frames)
        elif self.id == b'rOBJ':
            self.robj = ROBJ(Bdict(self.content).dic)
            
        elif self.id == b'nGRP':
            _node_id = unpack_from('i', self.content)
            bdict=Bdict(self.content,4)
            _node_attr = bdict.dic
            children_num = int(unpack_from('i', self.content,bdict.offset)[0])
            child_ids = []
            offset=bdict.offset+4
            for i in range(children_num):
                child_ids.append(unpack_from('i',self.content,offset+4*i))
            self.ngrp=NGRP(_node_id,_node_attr,children_num,child_ids)

        elif self.id == b'nSHP':
            _node_id = unpack_from('i', self.content)
            bdict=Bdict(self.content,4)
            _node_attr = bdict.dic
            model_num = int(unpack_from('i', self.content,bdict.offset)[0])
            models=[]
            offset=bdict.offset+4
            for i in range(model_num):
                mod={}
                mod['_id']=unpack_from('i',self.content,offset)
                _bdict=Bdict(self.content,offset+4)
                mod['_attr_dic']=_bdict.dic
                offset=_bdict.offset
                models.append(mod)
            self.nshp=nSHP(_node_id,_node_attr,models)

        elif self.id == b'LAYR':
            _id = unpack_from('i', self.content)
            bdic=Bdict(self.content,4)
            _rev_id = unpack_from('i',self.content,bdic.offset)
            self.layer=Layer(_id,bdic.dic,_rev_id)

        elif self.id == b'rCAM':
            _id = unpack_from('i', self.content)
            _dict = Bdict(self.content,4).dic
            self.camera=Camera(_id,_dict)

        elif self.id == b'NOTE':
            num = int(unpack_from('i', self.content)[0])
            _name_list=[]
            offset=4
            for i in range(num):
                bstr=Bstring(self.content,offset)
                offset+=bstr.byte_length
                _name_list.append(bstr.string)

            self.palette_note=Note(num,_name_list)

        elif self.id == b'IMAP':
            pass


        else:
            raise ParsingException('Unknown chunk type: %s'%self.id)

class Vox():

    def __init__(self,chunks):
        self.chunks=chunks
        self.palettes = []
        self.sizes = []
        self.voxels = []
        self.materials = []
        self.robjs=[]
        self.layers=[]
        self.ngrps=[]
        self.ntrns=[]
        self.nshps=[]
        self.cameras=[]
        self.palette_notes=[]
        self._parse_chunk()

        pass

    def _parse_chunk(self):
        for chunk in self.chunks:
            chunk:Chunk
            if chunk.id==b'RGBA':
                self.palettes.append(chunk.palette)
            elif chunk.id==b'SIZE':
                self.sizes.append(chunk.size)
            elif chunk.id==b'XYZI':
                self.voxels.append(chunk.voxels)
            elif chunk.id==b"LAYR":
                self.layers.append(chunk.layer)
            elif chunk.id==b'MATL':
                self.materials.append(chunk.material)
            elif chunk.id==b'rOBJ':
                self.robjs.append(chunk.robj)
            elif chunk.id==b'nTRN':
                self.ntrns.append(chunk.ntrn)
            elif chunk.id==b'nGRP':
                self.ngrps.append(chunk.ngrp)
            elif chunk.id==b'nSHP':
                self.nshps.append(chunk.nshp)
            elif chunk.id==b'rCAM':
                self.cameras.append(chunk.camera)
            elif chunk.id==b'NOTE':
                self.palette_notes.append(chunk.palette_note)


    def to_list(self,vox_index=0,palette_index=0):
        l,w,h=self.sizes[vox_index]
        arr=np.zeros((l,w,h,4))
        color=np.array(self.palettes[palette_index])
        for i in self.voxels[vox_index]:
            x=i[0]
            y=i[1]
            z=i[2]
            c=i[3]
            arr[x,y,z]=color[c-1]/255
        return arr
    

    @property
    def palette(self):
        return self._palette

    @palette.setter
    def palette(self, val:list):
        if isinstance(val,list) and np.array(val).shape==(255,4):
            self._palette = val
            self.default_palette = False
        else:
            raise AssigningException('The value seems not a palette.')

    pass