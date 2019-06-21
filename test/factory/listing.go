package factory

import (
	"github.com/OpenBazaar/openbazaar-go/pb"
	"github.com/golang/protobuf/ptypes/timestamp"
)

func NewListing(slug string) *pb.Listing {
	coupons := []*pb.Listing_Coupon{}
	sampleCoupon := new(pb.Listing_Coupon)
	sampleCoupon.Title = "sample coupon"
	sampleCoupon.Code = &pb.Listing_Coupon_DiscountCode{DiscountCode: "insider"}
	sampleCoupon.Discount = &pb.Listing_Coupon_PercentDiscount{PercentDiscount: 5.0}
	// sampleCoupon.Discount = &pb.Listing_Coupon_PriceDiscount{
	// 	PriceDiscount: &pb.CurrencyValue{
	// 		Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8},
	// 		Amount:   "50",
	// 	},
	// }
	coupons = append(coupons, sampleCoupon)
	return &pb.Listing{
		Slug:               slug,
		TermsAndConditions: "Sample Terms and Conditions",
		RefundPolicy:       "Sample Refund policy",
		Metadata: &pb.Listing_Metadata{
			Version:             1,
			AcceptedCurrencies:  []string{"TBTC"},
			PricingCurrencyDefn: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"},
			Expiry:              &timestamp.Timestamp{Seconds: 3147483647},
			Format:              pb.Listing_Metadata_FIXED_PRICE,
			ContractType:        pb.Listing_Metadata_PHYSICAL_GOOD,
		},
		Item: &pb.Listing_Item{
			Skus: []*pb.Listing_Item_Sku{
				{
					SurchargeValue: &pb.CurrencyValue{Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"}, Amount: "0"},
					Quantity:       12,
					ProductID:      "1",
					VariantCombo:   []uint32{0, 0},
				},
				{
					SurchargeValue: &pb.CurrencyValue{Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"}, Amount: "0"},
					Quantity:       44,
					ProductID:      "2",
					VariantCombo:   []uint32{0, 1},
				},
			},
			Title: "Ron Swanson Tshirt",
			Tags:  []string{"tshirts"},
			Options: []*pb.Listing_Item_Option{
				{
					Name:        "Size",
					Description: "What size do you want your shirt?",
					Variants: []*pb.Listing_Item_Option_Variant{
						{Name: "Small", Image: NewImage()},
						{Name: "Large", Image: NewImage()},
					},
				},
				{
					Name:        "Color",
					Description: "What color do you want your shirt?",
					Variants: []*pb.Listing_Item_Option_Variant{
						{Name: "Red", Image: NewImage()},
						{Name: "Green", Image: NewImage()},
					},
				},
			},
			Nsfw:        false,
			Description: "Example item",
			PriceValue: &pb.CurrencyValue{
				Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"},
				Amount:   "2000",
			},
			ProcessingTime: "3 days",
			Categories:     []string{"tshirts"},
			Grams:          14,
			Condition:      "new",
			Images:         []*pb.Listing_Item_Image{NewImage(), NewImage()},
		},
		Taxes: []*pb.Listing_Tax{
			{
				Percentage:  7,
				TaxShipping: true,
				TaxType:     "Sales tax",
				TaxRegions:  []pb.CountryCode{pb.CountryCode_UNITED_STATES},
			},
		},
		ShippingOptions: []*pb.Listing_ShippingOption{
			{
				Name:    "usps",
				Type:    pb.Listing_ShippingOption_FIXED_PRICE,
				Regions: []pb.CountryCode{pb.CountryCode_ALL},
				Services: []*pb.Listing_ShippingOption_Service{
					{
						Name:              "standard",
						PriceValue:        &pb.CurrencyValue{Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"}, Amount: "20"},
						EstimatedDelivery: "3 days",
					},
				},
			},
		},

		Coupons: coupons,
	}
}

func NewCryptoListing(slug string) *pb.Listing {
	listing := NewListing(slug)
	//listing.Metadata.CoinType = "TETH"
	//listing.Metadata.CoinDivisibility = 1e8
	listing.Metadata.ContractType = pb.Listing_Metadata_CRYPTOCURRENCY
	listing.Item.Skus = []*pb.Listing_Item_Sku{{Quantity: 1e8}}
	//listing.Metadata.PricingCurrency = &pb.CurrencyDefinition{Code: "ETH", Divisibility: 8}
	listing.Metadata.PricingCurrencyDefn = &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8}
	listing.ShippingOptions = nil
	listing.Item.Condition = ""
	listing.Item.Options = nil
	listing.Item.PriceValue = &pb.CurrencyValue{
		Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8},
		Amount:   "0",
	}
	listing.Coupons = nil
	return listing
}

func NewListingWithShippingRegions(slug string) *pb.Listing {
	listing := NewListing(slug)
	listing.ShippingOptions = []*pb.Listing_ShippingOption{
		{
			Name:    "usps",
			Type:    pb.Listing_ShippingOption_FIXED_PRICE,
			Regions: []pb.CountryCode{pb.CountryCode_UNITED_KINGDOM},
			Services: []*pb.Listing_ShippingOption_Service{
				{
					Name:              "standard",
					PriceValue:        &pb.CurrencyValue{Currency: &pb.CurrencyDefinition{Code: "TBTC", Divisibility: 8, Name: "A", CurrencyType: "A"}, Amount: "20"},
					EstimatedDelivery: "3 days",
				},
			},
		},
	}
	return listing
}
