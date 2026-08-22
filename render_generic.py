# Generic renderer: iso / front / top / side of the current design, fit-to-view.
# Usage: desktop_fusion_client.py run <this> -> renders D:\fusion_parts\<name>_{iso,front,top,side}.png
import adsk.core, adsk.fusion, time

app = adsk.core.Application.get()
vp = app.activeViewport
try:
    vp.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle
except Exception:
    pass

name = "part"
try:
    name = str(app.activeDocument.name).replace(" ", "_").replace(".", "_") or "part"
except Exception:
    pass

root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
bb = root.bRepBodies.item(0).boundingBox
cx = (bb.minPoint.x + bb.maxPoint.x) / 2.0
cy = (bb.minPoint.y + bb.maxPoint.y) / 2.0
cz = (bb.minPoint.z + bb.maxPoint.z) / 2.0
span = max(bb.maxPoint.x - bb.minPoint.x, bb.maxPoint.y - bb.minPoint.y, bb.maxPoint.z - bb.minPoint.z) + 1.0
dist = span * 3.0

def set_cam(eye, target, up, fit=True):
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.eye = adsk.core.Point3D.create(eye[0], eye[1], eye[2])
    cam.target = adsk.core.Point3D.create(target[0], target[1], target[2])
    cam.upVector = adsk.core.Vector3D.create(up[0], up[1], up[2])
    cam.isFitView = fit
    vp.camera = cam
    time.sleep(0.6)

set_cam((cx + dist, cy + dist, cz + dist), (cx, cy, cz), (0, 0, 1))
vp.saveAsImageFile("D:\\fusion_parts\\%s_iso.png" % name, 1000, 750)

set_cam((cx, cy, cz + dist), (cx, cy, cz), (0, 1, 0))
vp.saveAsImageFile("D:\\fusion_parts\\%s_top.png" % name, 1000, 750)

set_cam((cx - dist, cy, cz), (cx, cy, cz), (0, 0, 1))
vp.saveAsImageFile("D:\\fusion_parts\\%s_front.png" % name, 1000, 750)

set_cam((cx, cy - dist, cz), (cx, cy, cz), (0, 0, 1))
vp.saveAsImageFile("D:\\fusion_parts\\%s_side.png" % name, 1000, 750)

result = {"rendered": ["%s_iso" % name, "%s_top" % name, "%s_front" % name, "%s_side" % name]}
