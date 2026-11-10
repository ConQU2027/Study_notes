#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};




// Corresponds to lr_interfaces__srv__Climb_Request

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Climb_Request {

    // This member is not documented.
    #[allow(missing_docs)]
    pub target_height: i32,

}



impl Default for Climb_Request {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::Climb_Request::default())
  }
}

impl rosidl_runtime_rs::Message for Climb_Request {
  type RmwMsg = super::srv::rmw::Climb_Request;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        target_height: msg.target_height,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      target_height: msg.target_height,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      target_height: msg.target_height,
    }
  }
}


// Corresponds to lr_interfaces__srv__Climb_Response

// This struct is not documented.
#[allow(missing_docs)]

#[allow(non_camel_case_types)]
#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct Climb_Response {

    // This member is not documented.
    #[allow(missing_docs)]
    pub current_height: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub days: i32,

}



impl Default for Climb_Response {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::srv::rmw::Climb_Response::default())
  }
}

impl rosidl_runtime_rs::Message for Climb_Response {
  type RmwMsg = super::srv::rmw::Climb_Response;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        current_height: msg.current_height,
        days: msg.days,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      current_height: msg.current_height,
      days: msg.days,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      current_height: msg.current_height,
      days: msg.days,
    }
  }
}






#[link(name = "lr_interfaces__rosidl_typesupport_c")]
extern "C" {
    fn rosidl_typesupport_c__get_service_type_support_handle__lr_interfaces__srv__Climb() -> *const std::ffi::c_void;
}

// Corresponds to lr_interfaces__srv__Climb
#[allow(missing_docs, non_camel_case_types)]
pub struct Climb;

impl rosidl_runtime_rs::Service for Climb {
    type Request = Climb_Request;
    type Response = Climb_Response;

    fn get_type_support() -> *const std::ffi::c_void {
        // SAFETY: No preconditions for this function.
        unsafe { rosidl_typesupport_c__get_service_type_support_handle__lr_interfaces__srv__Climb() }
    }
}


