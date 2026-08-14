def telemetry_worker(processor, event): return processor.process(event)
def detection_worker(processor, event, detector): return processor.process(event, detector=detector)
def investigation_worker(processor, event, investigate):
    result = investigate(event.payload); processor.investigations.append(result); return result
def automation_worker(processor, event, automate):
    result = automate(event.payload); processor.automation_actions.append(result); return result
