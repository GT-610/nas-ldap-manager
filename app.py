from flask import Flask, request, redirect, url_for, flash, render_template 
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user 
from config import Config 
from ldap_manager import LDAPManager 
import ldap 
from flask_wtf.csrf  import CSRFProtect 
from datetime import datetime

# app.py  新增配置 
app = Flask(__name__, 
           template_folder='static/html',  # 指定模板目录 
           static_folder='static')
app.config.from_object(Config) 
csrf = CSRFProtect(app)
 
# 初始化组件 
login_manager = LoginManager(app)
login_manager.login_view  = 'login'
ldap_manager = LDAPManager()
 
# 用户会话代理 
class UserProxy(UserMixin):
    def __init__(self, uid):
        self.id  = uid  # LDAP uid作为唯一标识 
@app.route('/') 
def index():
    """带上下文变量的新版主页路由"""
    system_status = {
        'user_count': ldap_manager.get_user_count(), 
        'last_login': ldap_manager.get_last_login() 
    }
    return render_template('index.html',  
                         system_status=system_status,
                         current_time=datetime.now().strftime("%Y-%m-%d  %H:%M"))

@login_manager.user_loader  
def load_user(user_id):
    """必须实现的用户加载回调"""
    return UserProxy(user_id) if user_id else None 
 
# 核心路由 
@app.route('/register',  methods=['GET', 'POST'])
def register():
    if request.method  == 'POST':
        username = request.form.get('username',  '').strip()
        email = request.form.get('email',  '').strip()
        password = request.form.get('password',  '')
 
        # 基础验证 
        if not all([username, email, password]):
            flash('请填写所有必填字段')
            return redirect(url_for('register'))
 
        try:
            if ldap_manager.user_exists(username): 
                flash('该用户名已被注册')
                return redirect(url_for('register'))
                
            ldap_manager.add_user(username,  email, password)
            flash('注册成功，请登录')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(str(e))
            return redirect(url_for('register'))
 
    return render_template('register.html') 
 
@app.route('/login',  methods=['GET', 'POST'])
def login():
    if request.method  == 'POST':
        username = request.form.get('username') 
        password = request.form.get('password') 
        user_dn = f"uid={username},{app.config['LDAP_BASE_DN']}" 
 
        try:
            # 直接绑定验证 
            temp_conn = ldap.initialize(app.config['LDAP_URI']) 
            temp_conn.simple_bind_s(user_dn,  password)
            
            user = UserProxy(username)
            login_user(user)
            return redirect(url_for('dashboard'))
            
        except ldap.INVALID_CREDENTIALS:
            flash('用户名或密码错误')
        except ldap.LDAPError as e:
            flash('系统错误，请稍后再试')
        
        return redirect(url_for('login'))
    
    return render_template('login.html') 
 
@app.route('/logout') 
@login_required 
def logout():
    logout_user()
    return redirect(url_for('login'))
 
@app.route('/dashboard')
@login_required 
def dashboard():
    return render_template('dashboard.html')

# app.py
@app.route('/api/user-profile')
def user_profile():
    # 返回用户概况的内容
    return render_template('sub-pages/user_profile.html', 
        username=current_user.id
    )

# app.py
@app.route('/api/change-password', methods=['GET', 'POST'])
@login_required  # 确保用户已登录
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 验证输入
        if not all([old_password, new_password, confirm_password]):
            return {'success': False, 'message': '请填写所有字段'}

        if new_password != confirm_password:
            return {'success': False, 'message': '两次输入的新密码不一致'}

        try:
            # 验证原密码是否正确
            user_dn = f"uid={current_user.id},{app.config['LDAP_BASE_DN']}"
            temp_conn = ldap.initialize(app.config['LDAP_URI'])
            temp_conn.simple_bind_s(user_dn, old_password)

            # 更新密码
            ldap_manager.change_password(current_user.id, new_password)
            return {'success': True, 'message': '密码修改成功'}
        except ldap.INVALID_CREDENTIALS:
            return {'success': False, 'message': '原密码错误'}
        except Exception as e:
            return {'success': False, 'message': f'系统错误: {str(e)}'}

    # GET 请求返回修改密码页面
    return render_template('sub-pages/change_password.html')

# app.py
@app.route('/api/system_status')
def system_status():
    """提供系统状态JSON数据"""
    try:
        # 尝试连接 LDAP 数据库
        ldap_manager.conn  # 调用 LDAPManager 的 conn 属性会自动尝试连接
        service_status = "服务正常"
    except ldap.LDAPError as e:
        app.logger.error(f"LDAP 连接失败: {str(e)}")
        service_status = "服务不可用"

    return {
        'user_count': ldap_manager.get_user_count(),
        'last_login': ldap_manager.get_last_login(),
        'current_time': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'service_status': service_status  # 新增字段：服务状态
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0',  port=5000, debug=True)