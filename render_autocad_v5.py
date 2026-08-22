# Render autocad_bracket v5: fit-to-view framing
import adsk.core, adsk.fusion, math, time

app = adsk.core.Application.get()
vp = app.activeViewport
try:
    vp.visualStyle = adsk.core.VisualStyles.ShadedVisualStyle
except Exception:
    pass

def set_cam(eye, target, up, fit=True):
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.eye = adsk.core.Point3D.create(eye[0], eye[1], eye[2])
    cam.target = adsk.core.Point3D.create(target[0], target[1], target[2])
    cam.upVector = adsk.core.Vector3D.create(up[0], up[1], up[2])
    cam.isFitView = fit
    vp.camera = cam
    time.sleep(0.5)

cx, cy, cz = -6.7, -10.85, 5.0

set_cam((cx + 160, cy + 160, cz + 220), (cx, cy, cz), (0, 0, 1))
vp.saveAsImageFile("D:\\fusion_parts\\autocad_bracket_v5_iso.png", 1000, 750)

set_cam((cx, cy, cz + 300), (cx, cy, cz), (0, 1, 0))
vp.saveAsImageFile("D:\\fusion_parts\\autocad_bracket_v5_top.png", 1000, 750)

set_cam((cx + 240, cy - 160, cz + 60), (cx, cy, cz), (0, 0, 1))
vp.saveAsImageFile("D:\\fusion_parts\\autocad_bracket_v5_side.png", 1000, 750)

result = {"rendered": ["v5_iso", "v5_top", "v5_side"]}
