from rest_framework import serializers

class CommentSerializer(serializers.Serializer):
    email = serializers.CharField()
    content = serializers.CharField()
    created = serializers.DateTimeField()