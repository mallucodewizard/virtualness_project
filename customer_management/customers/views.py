import pandas as pd
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework import viewsets
from .models import Customer
from .serailizers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        email = request.data.get('email')
        phone = request.data.get('phone')
        
        # Check for existing customers with the same email or phone
        existing_customer = Customer.objects.filter(Q(email=email) | Q(phone=phone)).first()
        
        if existing_customer:
            # Update existing customer with the new data (most recent data wins)
            for field, value in request.data.items():
                if field in [f.name for f in Customer._meta.get_fields() if f.name not in ['id', 'custom_fields', 'is_active']]:
                    setattr(existing_customer, field, value)
                elif field in existing_customer.custom_fields:
                    existing_customer.custom_fields[field] = value
                else:
                    existing_customer.custom_fields[field] = value
            existing_customer.save()
            return Response({'message': 'Existing customer updated successfully'})
        else:
            serializer = CustomerSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request,pk=None):
        data = request.data
        id = pk
        instance = Customer.objects.filter(id=id).first()
        if not instance:
            return Response({'error': 'Invalid id'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CustomerSerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
    def destroy(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            customer.delete()
            return Response(
                data={
                    "message": "Customer deleted successfully",
                    "status": "success",
                },
                status=200,
            )
        except Customer.DoesNotExist:
            return Response(
                data={"message": "Customer not found", "status": "failure"},
                status=200,
            )

 
    @action(detail=False, methods=['post'])
    def create_segment(self, request):
        # Example segmentation logic based on custom criteria
        criteria = request.data.get('criteria', {})
        segment = self.queryset.filter(**criteria)
        serializer = self.get_serializer(segment, many=True)

        if request.data.get('operation') == 'export':
            doc_type = request.data.get('doc_type', 'xlsx')  # Change to xlsx
            df = pd.DataFrame(serializer.data)

            # Export to Excel or CSV
            if doc_type == 'xlsx':
                df.to_excel('segment.xlsx', index=False, engine='openpyxl')
            elif doc_type == 'csv':
                df.to_csv('segment.csv', index=False)
            else:
                return Response({'error': 'Invalid doc_type. Must be xlsx or csv.'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'message': f'Segment exported as {doc_type}. check out your project folder'})

        return Response(serializer.data)