from rest_framework.serializers import ModelSerializer

from modules.authority.models import Role
from modules.user.models import Users, UserProfile, UserAuthority


class UserSerializers(ModelSerializer):
    class Meta:
        model = Users
        field = "__all__"
        exclude = ['password']

    def to_representation(self, obj):  # 此函数在序列化时才会用到，用于自定义输出
        ret = super(UserSerializers, self).to_representation(obj)
        profile = UserProfile.objects.get(id=obj.id)
        user_role = []
        user_role_ids = UserAuthority.objects.filter(user=obj.id).values(*['role'])
        for role in user_role_ids:
            role_queryset = Role.objects.get(id=role['role'])
            role_obj = {'id': role_queryset.id, 'name': role_queryset.name}
            user_role.append(role_obj)
        ret["profile"] = profile
        ret["roles"] = user_role
        return ret
