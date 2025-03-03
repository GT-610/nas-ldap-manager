import ldap 
import hashlib 
import base64 
import os 
from flask import current_app 
 
class LDAPManager:
    def __init__(self):
        self._conn = None 
 
    @property 
    def conn(self):
        """保持长连接的可复用LDAP连接"""
        if not self._conn or not self._conn.whoami_s(): 
            self._conn = ldap.initialize(current_app.config['LDAP_URI']) 
            self._conn.simple_bind_s( 
                current_app.config['LDAP_ADMIN_DN'], 
                current_app.config['LDAP_ADMIN_PW'] 
            )
        return self._conn 
 
    def user_exists(self, username):
        """检查用户名是否已存在"""
        search_filter = f"(uid={username})"
        try:
            results = self.conn.search_s( 
                current_app.config['LDAP_BASE_DN'], 
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['uid']
            )
            return len(results) > 0 
        except ldap.LDAPError as e:
            current_app.logger.error(f"LDAP 查询失败: {str(e)}")
            return False 
 
    def get_user_count(self):
        """获取已注册用户总数"""
        search_filter = "(objectClass={})".format(
            current_app.config['LDAP_USER_OBJECT_CLASS'] 
        )
        try:
            results = self.conn.search_s( 
                current_app.config['LDAP_BASE_DN'], 
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['uid']
            )
            return len(results)
        except ldap.LDAPError as e:
            current_app.logger.error(f" 用户统计失败: {str(e)}")
            return 0 
    
    def get_last_login(self):
        """获取最近登录时间（假设使用loginTime属性）"""
        search_filter = "(&(objectClass={})(loginTime=*))".format(
            current_app.config['LDAP_USER_OBJECT_CLASS'] 
        )
        try:
            results = self.conn.search_s( 
                current_app.config['LDAP_BASE_DN'], 
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['loginTime'],
            )
            if results:
                # 转换时间戳：假设存储为UTC时间戳 
                timestamp = int(results[0][1]['loginTime'][0].decode())
                return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d  %H:%M")
            return "暂无记录"
        except ldap.LDAPError as e:
            current_app.logger.error(f" 登录记录查询失败: {str(e)}")
            return "系统错误"

    def add_user(self, username, email, password):
        """添加新用户到LDAP目录"""
        dn = f"uid={username},{current_app.config['LDAP_BASE_DN']}" 
        hashed_pw = self._generate_ssha(password)
        
        entry = {
            'objectClass': current_app.config['LDAP_USER_OBJECT_CLASS'], 
            'uid': [username.encode('utf-8')],
            'mail': [email.encode('utf-8')],
            'userPassword': [hashed_pw],
            'sn': [username.encode('utf-8')],      # inetOrgPerson必填字段 
            'cn': [username.encode('utf-8')]       # 通用名称字段 
        }
 
        try:
            self.conn.add_s(dn,  ldap.modlist.addModlist(entry)) 
            return True 
        except ldap.ALREADY_EXISTS:
            raise ValueError("用户名已被注册")
        except ldap.LDAPError as e:
            current_app.logger.error(f" 用户创建失败: {str(e)}")
            raise RuntimeError("系统错误，请联系管理员")
 
    def change_password(self, username, new_password):
        """
        修改用户密码
        :param username: 用户名
        :param new_password: 新密码
        """
        user_dn = f"uid={username},{current_app.config['LDAP_BASE_DN']}"
        hashed_pw = self._generate_ssha(new_password)  # 使用现有的SSHA哈希方法生成密码

        # 构造修改列表
        mod_list = [(ldap.MOD_REPLACE, 'userPassword', [hashed_pw])]

        try:
            # 执行修改操作
            self.conn.modify_s(user_dn, mod_list)
        except ldap.LDAPError as e:
            current_app.logger.error(f"密码修改失败: {str(e)}")
            raise RuntimeError("系统错误，请稍后再试")
    def _generate_ssha(self, password):
        """生成LDAP兼容的SSHA密码哈希"""
        salt = os.urandom(4) 
        sha = hashlib.sha1(password.encode('utf-8')) 
        sha.update(salt) 
        digest_salt = sha.digest()  + salt 
        return b"{SSHA}" + base64.b64encode(digest_salt)