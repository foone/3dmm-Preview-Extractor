from lib3dmm import c3dmmFile
import sys
from PIL import Image
from cStringIO import StringIO
from error import CompressedError
from struct import unpack

PALETTE = """eJz7z/D/P24U4ryRsb7+/fv3AgICoqKi3Nzc0tLSOjo6np6eaWlpxcXF9Q0NU6ZMWb169bZt244c
OXLx4sV79+69fPny48ePP3/+FBfXl5Y2k5B3VtSJMbHv9nJcEOK5JT3mdFnOhdqor+3pX/sKv7dX
/Vrc+mfL7L+7NvzVkRZw1ZLMdlGfGGu2scjpZIP33Z6gF1NDXyyMfrEx4cW2rBcH0l8cKHhxIv/F
hYIX56ssuLlCpCTKZWR6JXhWywmdE5d5o6DwwslJRE5HydDDwCXV3K/YLrzJNbHfv2BZUuPmLm6v
jXwJNwVL3wg3vFXvemcz9WPE0s9lW+2lGDO0mSbZMi93Zd7tx3IhjOV9JuuvSmkdHhNP4fA0mcoy
+e4W5TmT1deu1D2x3eFqnDtTRzrTxi7mY7NYbm9j+XCc5dcl6d83LY2M+EJCxEpKFFta1KZO1V66
1GDvXvNTp7w0pMSdddTjbM2zXe0r/N3bwv1npUStKM0RM+JTDRY3KVG0alV1nqrtuUw/dJ9Z2mlP
TTFxV1X1RBOzfBu7Gme3Li/f+aGRa9Oz2CxVuRLt+NrDBGYlC60tEDlQLXajS/nlLGVlZSsrq5CQ
kJiYGGNjYzwROorQEAB28ZHR""".decode('base64').decode('zlib')

def findFirstScene(movie):
	mvie = None
	for quad in movie.quads:
		if quad['type']=='MVIE':
			mvie = quad
	if mvie:
		refs=sorted(mvie['references'],key=lambda ref:ref['ref_id'])
		SCENs=[ref for ref in refs if ref['type']=='SCEN']
		return SCENs[0]
		

def findFirstThum(movie):
	scene = findFirstScene(movie)
	scene_quad = movie.find_quad(scene['type'],scene['id'])
	thum = [ref for ref in scene_quad['references'] if ref['type']=='THUM'][0]
	
	return movie.find_quad(thum['type'], thum['id'])

def extractPIL(quad):
	fop = StringIO(quad['source'].get())

	strmarker=fop.read(4)
	marker=unpack('<4B',strmarker)
	if strmarker in ('KCDC','KCD2'):
		raise CompressedError,'Section is compressed'
	if marker not in ((1,0,3,3),(1,0,5,5)):	raise LoadError('Bad marker')
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



def getImageFromMovie(path):
	movie = c3dmmFile(path)
	thumb = findFirstThum(movie)
	im = extractPIL(thumb)
	return im 

def dumpPNG(im):
	io = StringIO()
	im.save(io, 'png')
	sys.stdout.write(io.getvalue())

if __name__=='__main__':
	im=getImageFromMovie(sys.argv[1])

	out_file = sys.argv[2]

	if out_file == '-':
		dumpPNG(im)
	else:
		im.save(sys.argv[2])