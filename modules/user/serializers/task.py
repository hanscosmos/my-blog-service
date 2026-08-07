from rest_framework.serializers import ModelSerializer


from modules.user.models import Users, UserProfile, UserAuthority, UserTask


class UserTaskSerializers(ModelSerializer):
    class Meta:
        model = UserTask
        field = "__all__"
        exclude = []

    def to_representation(self, obj):  # 此函数在序列化时才会用到，用于自定义输出
        ret = super(UserTaskSerializers, self).to_representation(obj)
        ret['score'] = obj.value_score
        ret['tags'] = obj.tags.split(',')
        return ret
