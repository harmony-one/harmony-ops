package main

import (
	pd "github.com/PagerDuty/go-pagerduty"
)

func notify(serviceKey, incidentKey, chain, msg string) error {
	_, err := pd.ManageEvent(pd.V2Event{
			RoutingKey: serviceKey,
			Action:     "trigger",
			DedupKey:   incidentKey,
			Payload: &pd.V2Payload{
				Summary:  incidentKey,
				Source:   chain,
				Severity: "critical",
				Details:  msg,
			},
		})
	return err
}
