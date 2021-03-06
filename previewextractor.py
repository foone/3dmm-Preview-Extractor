from lib3dmm import c3dmmFile
import sys
from PIL import Image
from cStringIO import StringIO
from error import CompressedError,LoadError
from struct import unpack
from zipfile import ZipFile, BadZipfile
from rarfile import RarFile
import argparse

PALETTE = """
eJxjYGBoYADhBjDVAGYdOHBAPtVTf3puiPNGhvr6f///CwgIiIqKcnNzS0tL6+joeHp6pqWlFRcX
NzQ0TJkyZfXq1du2bTty5MjFixfv3bv38uXLjx8//vz5U1xcX1raTELeWVEnxsS+28txQYjnlvSY
02U5F2qjvranf+0r/N5e9Wtx658ts//u2vBXR1rAVUsy20V9YqzZxiKnkw3ed3uCXkwNfbEw+sXG
hBfbsl4cSH9xoODFifwXFwpenK+y4OYKkZIol5HpleBZLSd0TlzmjYLCCycnETkdJUMPA5dUc79i
u/Am18R+/4JlSY2bu7i9NvIl3BQsfSPc8Fa9653N1I8RSz+XbbWXYszQZppky7zclXm3H8uFMJb3
may/KqV1eEw8hcPTZCrL5LtblOdMVl+7UvfEdoerce5MHelMG7uYj81iub2N5cNxll+XpH/ftDQy
4gsJESspUWxpUZs6VXvpUoO9e81PnfLSkBJ31lGPszXPdrWv8HdvC/eflRK1ojRHzIhPNVjcpETR
qlXVeaq25zL90H1maac9NcXEXVXVE03M8m3sapzdurx854dGrk3PYrNU5Uq042sPE5iVLLS2QORA
tdiNLuWXs5SVla2srEJCQmJiYoyNjRn+M4wiOFqwYAkwlQKZQPZ/MPUfzPoP5gAAt7Qomg==""".strip().decode('base64').decode('zlib')

def getSceneList(movie):
	mvie = None
	for quad in movie.quads:
		if quad['type']=='MVIE':
			mvie = quad
	if mvie:
		refs=sorted(mvie['references'],key=lambda ref:ref['ref_id'])
		SCENs=[movie.find_quad(ref['type'],ref['id']) for ref in refs if ref['type']=='SCEN']
		return SCENs
		

def findFirstThum(movie, scenes):
	scene_quad = scenes[0]
	thum = [ref for ref in scene_quad['references'] if ref['type']=='THUM'][0]
	
	return movie.find_quad(thum['type'], thum['id'])

def extractPIL(quad):
	fop = StringIO(quad['source'].get())

	strmarker=fop.read(4)
	marker=unpack('<4B',strmarker)
	if strmarker in ('KCDC','KCD2'):
		raise CompressedError,'Section is compressed'
	if marker not in ((1,0,3,3),(1,0,5,5)):	raise LoadError('Bad marker: %s' % (marker,))
	junk,x,y,w,h,filesize=unpack('<6l',fop.read(24))
	w-=x
	h-=y
	linelengths=unpack('<%iH' % (h),fop.read(2*h))
	surf = Image.new('P', (w,h))
	
	surf.putpalette(PALETTE)
	for line in range(h):
		if linelengths[line]!=0:
			linepos=0
			xpos=0
			while linepos<linelengths[line]:
				skip,linesize=unpack('<2B',fop.read(2))
				xpos+=skip
				linepos+=2
				lineimage = Image.frombytes('P',(linesize,1),fop.read(linesize))
				surf.paste(lineimage, (xpos,line))
				linepos+=linesize
	return surf


def loadMovieFromArchive(archive):
	for filename in archive.namelist():
		if filename.lower().endswith(('.3mm','.vmm')):
			movie = c3dmmFile()
			movie.loadFromObject(StringIO(archive.read(filename)))
			return movie
	raise LoadError('No 3mm/vmm found in archive')


def loadMovie(path):
	try:
		return c3dmmFile(path)
	except LoadError as err:
		if 'Not a 3mm/vmm file' in str(err):
			try:
				return loadMovieFromArchive(ZipFile(path))
			except BadZipfile:
				return loadMovieFromArchive(RarFile(path))
		else:
			raise

def getImageFromMovie(path):
	movie = loadMovie(path)
	scenes = getSceneList(movie)
	thumb = findFirstThum(movie, scenes)
	im = extractPIL(thumb)
	return im 

def dumpPNG(im):
	io = StringIO()
	im.save(io, 'png')
	sys.stdout.write(io.getvalue())

if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('movie', help='.3mm/.vmm(or .zip/.rar containing same) of movie to extract previews from')
	parser.add_argument('image', help='image path to write to (- to dump PNG to stdout)')


	args=parser.parse_args()

	im=getImageFromMovie(args.movie)


	if args.image == '-':
		dumpPNG(im)
	else:
		im.save(args.image)