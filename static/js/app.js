// 初始化MDUI组件
document.addEventListener('DOMContentLoaded',  function() {
    mdui.updateTextFields(); 
    
    // 全局消息提示
    const snackbar = new mdui.Snackbar('#globalSnackbar', {
        position: 'right-bottom',
        timeout: 4000
    });

    // 显示Flash消息
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                snackbar.open({ 
                    message: '{{ message }}',
                    closeOnOutside: true,
                    buttonText: '关闭',
                    buttonColor: mdui.snackbar.defaults.buttonColor 
                });
            {% endfor %}
        {% endif %}
    {% endwith %}
});

// 动态密码强度检测
document.querySelectorAll('input[type="password"]').forEach(input  => {
    input.addEventListener('input',  function() {
        const strengthBar = this.parentElement.querySelector('.password-strength'); 
        if (!strengthBar) return;

        const score = calculatePasswordStrength(this.value); 
        strengthBar.style.width  = `${score * 25}%`;
        strengthBar.style.backgroundColor  = getStrengthColor(score);
    });
});

// 在app.js 中添加 
document.querySelector('input[name="password"]').addEventListener('input',  function(e) {
    const strengthMeter = document.getElementById('strength-meter'); 
    const strength = calculatePasswordStrength(e.target.value); 
    strengthMeter.style.width  = `${strength}%`;
});
function calculatePasswordStrength(pw) {
    let score = 0;
    if (pw.length  >= 8) score++;
    if (pw.match(/[A-Z]/))  score++;
    if (pw.match(/[0-9]/))  score++;
    if (pw.match(/[^A-Za-z0-9]/))  score++;
    return Math.min(4,  score);
}

function getStrengthColor(score) {
    const colors = ['#f44336', '#FF9800', '#FFC107', '#4CAF50'];
    return colors[Math.min(score, 3)];
}