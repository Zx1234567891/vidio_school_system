#!/bin/bash
# 修复路由文件 - 移除 response_model 参数

cd D:/vidio_school_system/apps/api/app/routers

# 修复 events.py
sed -i 's/@router.get("", response_model=ResponseModel)/@router.get("")/g' events.py
sed -i 's/@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)/@router.post("", status_code=status.HTTP_201_CREATED)/g' events.py
sed -i 's/@router.get("\/{event_id}", response_model=ResponseModel)/@router.get("\/{event_id}")/g' events.py
sed -i 's/@router.put("\/{event_id}", response_model=ResponseModel)/@router.put("\/{event_id}")/g' events.py
sed -i 's/@router.delete("\/{event_id}", response_model=ResponseModel)/@router.delete("\/{event_id}")/g' events.py
sed -i 's/@router.get("\/stats\/overview", response_model=ResponseModel)/@router.get("\/stats\/overview")/g' events.py

# 修复 clips.py
sed -i 's/@router.get("", response_model=ResponseModel)/@router.get("")/g' clips.py
sed -i 's/@router.post("\/export", response_model=ResponseModel, status_code=status.HTTP_202_ACCEPTED)/@router.post("\/export", status_code=status.HTTP_202_ACCEPTED)/g' clips.py
sed -i 's/@router.get("\/{clip_id}", response_model=ResponseModel)/@router.get("\/{clip_id}")/g' clips.py
sed -i 's/@router.delete("\/{clip_id}", response_model=ResponseModel)/@router.delete("\/{clip_id}")/g' clips.py

# 修复 reviews.py
sed -i 's/@router.get("", response_model=ResponseModel)/@router.get("")/g' reviews.py
sed -i 's/@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)/@router.post("", status_code=status.HTTP_201_CREATED)/g' reviews.py
sed -i 's/@router.get("\/{review_id}", response_model=ResponseModel)/@router.get("\/{review_id}")/g' reviews.py
sed -i 's/@router.get("\/event\/{event_id}", response_model=ResponseModel)/@router.get("\/event\/{event_id}")/g' reviews.py

# 修复 training.py
sed -i 's/@router.get("", response_model=ResponseModel)/@router.get("")/g' training.py
sed -i 's/@router.post("", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)/@router.post("", status_code=status.HTTP_201_CREATED)/g' training.py
sed -i 's/@router.get("\/{job_id}", response_model=ResponseModel)/@router.get("\/{job_id}")/g' training.py
sed -i 's/@router.put("\/{job_id}", response_model=ResponseModel)/@router.put("\/{job_id}")/g' training.py
sed -i 's/@router.post("\/{job_id}\/start", response_model=ResponseModel)/@router.post("\/{job_id}\/start")/g' training.py
sed -i 's/@router.post("\/{job_id}\/cancel", response_model=ResponseModel)/@router.post("\/{job_id}\/cancel")/g' training.py
sed -i 's/@router.delete("\/{job_id}", response_model=ResponseModel)/@router.delete("\/{job_id}")/g' training.py

# 修复 metrics.py
sed -i 's/@router.get("\/system", response_model=ResponseModel)/@router.get("\/system")/g' metrics.py
sed -i 's/@router.get("\/streams", response_model=ResponseModel)/@router.get("\/streams")/g' metrics.py
sed -i 's/@router.get("\/streams\/{stream_id}", response_model=ResponseModel)/@router.get("\/streams\/{stream_id}")/g' metrics.py
sed -i 's/@router.get("\/dashboard", response_model=ResponseModel)/@router.get("\/dashboard")/g' metrics.py

echo "All router files fixed!"
