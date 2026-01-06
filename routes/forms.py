from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp, Optional

class AddEngineerForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=20),
                                        Regexp(r'^[A-Za-z0-9]+$', message='用户名只能包含字母和数字')])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('添加工程师')

# 添加员工表单（支持工程师、客服、试岗）
class AddEmployeeForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=20),
                                        Regexp(r'^[A-Za-z0-9]+$', message='用户名只能包含字母和数字')])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码不一致')])
    role_level = SelectField('角色级别', choices=[(3, '正式员工'), (4, '试岗员工')], coerce=int)
    role_detail = SelectField('详细角色 (正式员工选择)', choices=[('engineer', '工程师'), ('customer_service', '客服')], 
                             validators=[Optional()], coerce=str)
    submit = SubmitField('添加员工')

# 添加登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('登录')

# 添加注册表单
class RegisterForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=20), 
                                        Regexp(r'^[A-Za-z0-9]+$', message='用户名只能包含字母和数字')])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码不一致')])
    submit = SubmitField('注册')

# 添加管理员表单（修正权限级别选项）
class AddAdminForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('用户名', validators=[DataRequired(), Length(min=4, max=20),
                                        Regexp(r'^[A-Za-z0-9]+$', message='用户名只能包含字母和数字')])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码不一致')])
    role_level = SelectField('权限级别', choices=[(0, '超级管理员'), (1, '高级管理员'), (2, '普通管理员')], coerce=int)
    submit = SubmitField('添加')

# 添加超级管理员编辑表单
class EditSuperAdminForm(FlaskForm):
    new_name = StringField('新姓名', validators=[DataRequired(), Length(min=2, max=50)])
    new_username = StringField('新用户名', validators=[DataRequired(), Length(min=4, max=20),
                                        Regexp(r'^[A-Za-z0-9]+$', message='用户名只能包含字母和数字')])
    new_password = PasswordField('新密码 (不修改请留空)', validators=[Optional(), Length(min=8)])
    submit = SubmitField('保存修改')

class EditUserForm(FlaskForm):
    new_name = StringField('新姓名', validators=[DataRequired(), Length(min=2, max=50)])
    new_password = PasswordField('新密码 (不修改请留空)', validators=[Optional(), Length(min=8)])
    submit = SubmitField('保存修改')