class RatingEngine:
 def rate(self,repository,org,package_id,rating,feedback=""):
  item={"organization_id":org,"package_id":package_id,"rating":max(1,min(5,int(rating))),"feedback":feedback}; repository.ratings.append(item); return item
