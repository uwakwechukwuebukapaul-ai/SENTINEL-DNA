def calculate_attack_coverage(covered, total): return round(len(set(covered))/max(1,len(set(total)))*100,2)
def calculate_detection_depth(rules): return round(sum(len(getattr(r,"mitre_techniques",[])) for r in rules)/max(1,len(rules)),2)
def calculate_visibility_score(covered,total,rules): return round((calculate_attack_coverage(covered,total)+min(100,calculate_detection_depth(rules)*20))/2,2)
