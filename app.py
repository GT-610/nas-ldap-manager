from flask import Flask, request, redirect, url_for, flash, render_template 
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user 
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
    return "用户仪表板（待实现）"
 
@app.route('/api/system_status') 
def system_status():
    """提供系统状态JSON数据"""
    return {
        'user_count': ldap_manager.get_user_count(), 
        'last_login': ldap_manager.get_last_login(), 
        'current_time': datetime.now().strftime("%Y-%m-%d  %H:%M")
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0',  port=5000, debug=True)