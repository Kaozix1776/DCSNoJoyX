import math
import math
from transformations import *
from configs import *
from utils import *
from DCSTelem import *

class dcs_cam_control():
    def __init__(self, win_w, win_h, con):
        self.cx = win_w /2
        self.cy = win_h /2
        self.fx = self.fy = win_w/2/math.tan(DEFAULT_FOV/2)
        self.is_free_look = False
        self.last_free_look = False
        self.con = con
        self.telem = con.telem

        self.q_view_abs = None
        self.dir_view_abs = np.array([1, 0, 0], dtype=float)

        self.view_yaw = 0
        self.view_pitch = 0

        print(f"Camera cx {self.cx} cy{self.cy} fx {self.fx} fy {self.fy}")

    def reset(self):
        print("reset dcs cam with self con", self.con.OK)
        self.q_cam_pitch_offset = quaternion_from_euler(0, CAM_PITCH_OFFSET, 0)
        if self.con.OK:
            if ACTIVE_CTRL_VIEW:
                self.q_view_abs = self.con.q_att_tgt.copy()
                self.dir_view_abs = self.con.dir_tgt.copy()
            else:
                self.update_view_from_telem()

    def update_view_from_telem(self):
        self.q_view_abs = self.telem.q_telem_cam
        self.dir_view_abs = q_to_dir(self.q_view_abs)

    def set_mouse_free_look(self, _x, _y):
        if ACTIVE_CTRL_VIEW:
            self.is_free_look = True
            _x = _x / self.fx * view_rate
            _y = _y / self.fx * view_rate

            self.dir_view_abs += quaternion_rotate(self.q_view_abs, np.array([0, _x, _y], dtype=float))
            self.dir_view_abs = unit_vector(self.dir_view_abs)
            self.q_view_abs = dir_to_q(self.dir_view_abs)
            _, self.view_pitch, self.view_yaw = euler_from_quaternion(self.q_view_abs)
            # print(f"Free look yaw {self.view_yaw*57.3:3.1f} pitch {self.view_pitch*57.3:3.1f} ")
            self.last_free_look = True
        else:
            self.update_view_from_telem()
    
    def set_mouse_free_look_off(self):
        if ACTIVE_CTRL_VIEW:
            self.is_free_look = False
            if self.q_view_abs is None or self.last_free_look:
                self.q_view_abs, self.dir_view_abs = self.q_default_view()
                self.last_free_look = False
        else:
            self.update_view_from_telem()

    def q_default_view(self):
        q_view_sp = quaternion_multiply(self.q_cam_pitch_offset, self.con.q_att_sp)
        q_view_sp = setZeroRoll(q_view_sp)
        self.dir_view_abs = q_to_dir(q_view_sp)
        return q_view_sp, self.dir_view_abs

    def set_camera_view(self):
        if ACTIVE_CTRL_VIEW:
            if not self.is_free_look:
                q_view_sp =  quaternion_multiply(self.q_cam_pitch_offset, self.con.q_att_tgt)
                q_view_sp = setZeroRoll(q_view_sp)
                self.q_view_abs = quaternion_slerp(self.q_view_abs, q_view_sp, view_filter_rate)
                self.dir_view_abs = q_to_dir(self.q_view_abs)
            q_cam, T_cam = self.cameraPose()
            self.telem.set_camera_pose(q_cam, T_cam)
        
        _, self.view_pitch, self.view_yaw = euler_from_quaternion(self.q_view_abs)

    def cameraPose(self):
        # T is relative to our aircraft
        # mat = quaternion_matrix(quaternion_inverse(self.q_view_abs))[0:3,0:3]
        mat = quaternion_matrix(self.q_view_abs)[0:3,0:3]
        T_cam = mat @ [-CAMERA_X, 0, -CAMERA_Z]
        if ACTIVE_CTRL_F3:
            T_cam = mat @ [-CAMERA_X, 0, 0]
        return self.q_view_abs, T_cam
