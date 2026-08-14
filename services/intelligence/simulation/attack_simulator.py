class AttackSimulator:
 PHASES=("initial_access","execution","persistence","privilege_escalation","lateral_movement","impact")
 def simulate(self,twin,blocked_phases=None): return [p for p in self.PHASES if p not in set(blocked_phases or [])]
